"""Coordinates champ-select events: decides when to ask Claude and what to import.

The session websocket fires many times per second, so the coach only acts on
meaningful transitions: (1) picks start or someone locks/bans before I lock, (2) I lock.
Lock-in cancels any pick recommendation still in flight.
"""

from __future__ import annotations

import asyncio
import logging

from rich.console import Console
from rich.panel import Panel

from .champselect import DraftState, parse_session
from .config import Config
from .ddragon import GameData
from .lcu import actions
from .recommender import Loadout, NoPoolError, PickRecommendation, Recommender
from .runes import RuneMappingError, build_rune_page

log = logging.getLogger(__name__)
console = Console()


class Coach:
    """Event handler for champ select.

    lcu-driver runs every websocket event as its own task, so events arrive while Claude is
    still thinking. Instead of queueing them (which replays stale drafts), the coach keeps
    only the latest session, runs at most one pick task, and cancels it when I lock in.
    """

    def __init__(self, cfg: Config, data: GameData, recommender: Recommender | None = None):
        self.cfg = cfg
        self.data = data
        self.recommender = recommender or Recommender(cfg, data)
        self._pick_task: asyncio.Task | None = None
        self._loadout_task: asyncio.Task | None = None
        self.reset()

    def reset(self) -> None:
        for task in (getattr(self, "_pick_task", None), getattr(self, "_loadout_task", None)):
            if task and not task.done():
                task.cancel()
        self._pick_task = None
        self._loadout_task = None
        self._pick_key: tuple | None = None
        self._loadout_for: str | None = None
        self._latest: DraftState | None = None

    async def on_session(self, connection, session: dict) -> None:
        draft = parse_session(session, self.data.champion_name)
        self._latest = draft

        if draft.my_locked:
            self._cancel_pick()
            if draft.my_champion and self._loadout_for != draft.my_champion:
                self._loadout_for = draft.my_champion
                if self._loadout_task and not self._loadout_task.done():
                    self._loadout_task.cancel()
                self._loadout_task = asyncio.create_task(self._handle_loadout(connection, draft))
            return

        # Start as soon as picks begin (not only on my turn), so the answer is ready in time;
        # refresh only when someone locks or bans, never on hovers.
        if draft.pick_phase and self._pick_key != draft.key():
            self._pick_key = draft.key()
            self._cancel_pick()
            self._pick_task = asyncio.create_task(self._handle_pick(connection, draft))

    def _cancel_pick(self) -> None:
        if self._pick_task and not self._pick_task.done():
            self._pick_task.cancel()
        self._pick_task = None

    def _still_relevant(self, draft: DraftState) -> bool:
        latest = self._latest
        return latest is not None and not latest.my_locked and latest.key() == draft.key()

    async def _pickable_names(self, connection) -> set[str] | None:
        try:
            ids = await actions.get_pickable_ids(connection)
        except Exception:  # noqa: BLE001 - filter is best-effort
            log.debug("pickable-champion-ids unavailable", exc_info=True)
            return None
        if not ids:
            return None
        return {n for cid in ids if (n := self.data.champion_name(cid))}

    async def _handle_pick(self, connection, draft: DraftState) -> None:
        role = self.recommender.role(draft)
        pickable = await self._pickable_names(connection)
        cands, _ = self.recommender.candidates(draft, pickable)
        if not cands:
            hint = ("add champions under [player.pools]" if self.cfg.player.pick_scope == "pool"
                    else "check data/roles.toml")
            console.print(f"[yellow]No candidates for {role} ({hint}). Runes/build still come "
                          "after you lock in.[/yellow]")
            return
        console.print(f"[dim]Thinking about your pick ({role}, {len(cands)} candidates)...[/dim]")
        try:
            rec = await self.recommender.recommend_pick(draft, pickable)
        except (NoPoolError, asyncio.CancelledError):
            return
        except Exception as exc:  # noqa: BLE001 - keep the coach alive during champ select
            log.exception("Pick recommendation failed")
            console.print(f"[red]Pick recommendation failed: {exc}[/red]")
            return
        if self._still_relevant(draft):   # draft moved on or I locked: drop the stale answer
            render_pick(rec)

    async def _handle_loadout(self, connection, draft: DraftState) -> None:
        champion = draft.my_champion
        console.print(f"[dim]Preparing runes and build for {champion}...[/dim]")
        try:
            loadout = await self.recommender.recommend_loadout(draft, champion)
        except asyncio.CancelledError:
            return
        except Exception as exc:  # noqa: BLE001
            log.exception("Loadout recommendation failed")
            console.print(f"[red]Loadout recommendation failed: {exc}[/red]")
            return
        render_loadout(champion, loadout)

        if self.cfg.app.auto_import_runes:
            try:
                page = build_rune_page(loadout, self.data.rune_trees, self.cfg.app.rune_page_name)
                ok = await actions.import_rune_page(connection, page)
                console.print("[green]Rune page imported.[/green]" if ok else
                              "[yellow]Rune import failed, set runes manually.[/yellow]")
            except RuneMappingError as exc:
                console.print(f"[yellow]Could not map runes ({exc}). Set them manually.[/yellow]")

        if self.cfg.app.auto_set_summoner_spells:
            ids = [self.data.summoner_spells.get(s) for s in loadout.summoner_spells]
            if all(ids):
                await actions.set_summoner_spells(connection, ids[0], ids[1])


def render_pick(rec: PickRecommendation) -> None:
    alt = ", ".join(rec.alternatives) or "-"
    note = ("\n[yellow](model went outside the candidates, corrected)[/yellow]"
            if rec.corrected else "")
    tag = "  [green](comfort)[/green]" if rec.comfort else ""
    console.print(Panel(
        f"[bold]{rec.pick}[/bold]{tag}   alternatives: {alt}\n\n{rec.reasoning}{note}",
        title="Pick", border_style="cyan",
    ))


def render_loadout(champion: str, lo: Loadout) -> None:
    situational = "\n".join(f"  • {s['item']}: {s['when']}" for s in lo.situational) or "  -"
    tips = "\n".join(f"  • {t}" for t in lo.matchup_tips) or "  -"
    body = (
        f"[bold]Runes:[/bold] {lo.primary_tree}: {lo.keystone}, {', '.join(lo.primary_runes)}"
        f" | {lo.secondary_tree}: {', '.join(lo.secondary_runes)} | {', '.join(lo.shards)}\n"
        f"[bold]Spells:[/bold] {', '.join(lo.summoner_spells)}\n"
        f"[bold]Start:[/bold] {', '.join(lo.starting_items)}\n"
        f"[bold]Core:[/bold] {' → '.join(lo.core_items)}\n"
        f"[bold]Situational:[/bold]\n{situational}\n"
        f"[bold]Matchup tips:[/bold]\n{tips}\n\n{lo.reasoning}"
    )
    console.print(Panel(body, title=champion, border_style="magenta"))
