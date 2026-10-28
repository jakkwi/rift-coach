"""Turns the raw LCU champ-select session into a small, model-friendly DraftState.

Policy note: Riot requires that non-party summoner names stay hidden during ranked
champ select. DraftState deliberately contains champions and positions only, never names.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class AllyPick:
    position: str
    champion: str | None
    is_me: bool = False


@dataclass
class DraftState:
    my_position: str
    my_champion: str | None
    my_locked: bool
    my_turn_to_pick: bool
    pick_phase: bool = False        # at least one pick is in progress or done
    allies: list[AllyPick] = field(default_factory=list)
    enemies: list[str] = field(default_factory=list)
    bans: list[str] = field(default_factory=list)
    locked_allies: list[str] = field(default_factory=list)

    def key(self) -> tuple:
        """Changes only on locked picks and bans, never on hovers (mine or allies')."""
        return (
            self.my_position,
            tuple(sorted(self.locked_allies)),
            tuple(sorted(self.enemies)),
            tuple(sorted(self.bans)),
        )

    def unavailable(self) -> set[str]:
        taken = {a.champion for a in self.allies if a.champion and not a.is_me}
        return taken | set(self.enemies) | set(self.bans)


def parse_session(session: dict, champion_name: Callable[[int], str | None]) -> DraftState:
    me = session["localPlayerCellId"]
    actions = [a for group in session.get("actions", []) for a in group]

    my_pick_actions = [a for a in actions if a["actorCellId"] == me and a["type"] == "pick"]
    my_locked = any(a["completed"] for a in my_pick_actions)
    my_turn = any(a["isInProgress"] and not a["completed"] for a in my_pick_actions)
    pick_phase = any(
        a["type"] == "pick" and (a["isInProgress"] or a["completed"]) for a in actions
    )

    allies: list[AllyPick] = []
    my_position = ""
    my_champion = None
    for p in session.get("myTeam", []):
        champ_id = p.get("championId") or p.get("championPickIntent") or 0
        is_me = p["cellId"] == me
        pick = AllyPick(p.get("assignedPosition", ""), champion_name(champ_id), is_me)
        allies.append(pick)
        if is_me:
            my_position = pick.position
            my_champion = pick.champion

    enemies = [
        name
        for p in session.get("theirTeam", [])
        if (name := champion_name(p.get("championId", 0)))
    ]

    ban_ids = {a["championId"] for a in actions if a["type"] == "ban" and a["completed"]}
    bans_section = session.get("bans", {})
    ban_ids |= set(bans_section.get("myTeamBans", [])) | set(bans_section.get("theirTeamBans", []))
    bans = sorted(name for cid in ban_ids if (name := champion_name(cid)))

    ally_cells = {p["cellId"] for p in session.get("myTeam", [])} - {me}
    locked_allies = sorted(
        name
        for a in actions
        if a["type"] == "pick" and a["completed"] and a["actorCellId"] in ally_cells
        if (name := champion_name(a["championId"]))
    )

    return DraftState(
        my_position=my_position,
        my_champion=my_champion,
        my_locked=my_locked,
        my_turn_to_pick=my_turn,
        pick_phase=pick_phase or my_turn,
        allies=allies,
        enemies=enemies,
        bans=bans,
        locked_allies=locked_allies,
    )
