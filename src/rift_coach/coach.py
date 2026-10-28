"""Coordinates champ-select events: decides when to ask Claude and what to import.

The session websocket fires many times per second, so the coach only acts on
meaningful transitions: (1) it becomes my turn to pick, (2) I lock a champion.
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
from .recommender import Loadout, PickRecommendation, Recommender
from .runes import RuneMappingError, build_rune_page

log = logging.getLogger(__name__)
console = Console()


class Coach:
    def __init__(self, cfg: Config, data: GameData, recommender: Recommender | None = None):
        self.cfg = cfg
        self.data = data
        self.recommender = recommender or Recommender(cfg, data)
        self._lock = asyncio.Lock()
        self.reset()

    def reset(self) -> None:
        self._pick_key: tuple | None = None
        self._loadout_for: str | None = None

    async def on_session(self, connection, session: dict) -> None:
        draft = parse_session(session, self.data.champion_name)
        async with self._lock:
            if draft.my_turn_to_pick and self._pick_key != draft.key():
                self._pick_key = draft.key()
                await self._handle_pick(draft)
            if draft.my_locked and draft.my_champion and self._loadout_for != draft.my_champion:
                self._loadout_for = draft.my_champion
                await self._handle_loadout(connection, draft)

    async def _handle_pick(self, draft: DraftState) -> None:
        console.print("[dim]Thinking about your pick...[/dim]")
        try:
            rec = await self.recommender.recommend_pick(draft)
        except Exception as exc:  # noqa: BLE001 - keep the coach alive during champ select
            log.exception("Pick recommendation failed")
            console.print(f"[red]Pick recommendation failed: {exc}[/red]")
            return
        render_pick(rec)

    async def _handle_loadout(self, connection, draft: DraftState) -> None:
        champion = draft.my_champion
        console.print(f"[dim]Preparing runes and build for {champion}...[/dim]")
        try:
            loadout = await self.recommender.recommend_loadout(draft, champion)
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
    note = "\n[yellow](model went outside your pool, corrected)[/yellow]" if rec.corrected else ""
    console.print(Panel(
        f"[bold]{rec.pick}[/bold]   alternatives: {alt}\n\n{rec.reasoning}{note}",
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
