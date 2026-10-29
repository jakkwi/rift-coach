"""Builds a League Client item set (shown in the in-game shop) from a Loadout.

Also orders summoner spells for the player's Flash key.
"""

from __future__ import annotations

import uuid

from .recommender import Loadout

SUMMONERS_RIFT = 11


def _norm(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def resolve_items(names: list[str], item_ids: dict[str, str]) -> tuple[list[str], list[str]]:
    """(item ids found, names not found on this patch)."""
    lookup = {_norm(n): i for n, i in item_ids.items()}
    ids, missing = [], []
    for name in names:
        hit = lookup.get(_norm(name))
        (ids.append(hit) if hit else missing.append(name))
    return ids, missing


def build_item_set(
    loadout: Loadout, champion: str, champion_id: int, item_ids: dict[str, str], prefix: str
) -> tuple[dict, list[str]]:
    blocks_src = [
        ("Start", loadout.starting_items),
        ("Core (in order)", loadout.core_items),
        ("Situational", [s["item"] for s in loadout.situational]),
    ]
    blocks, missing_all = [], []
    for title, names in blocks_src:
        ids, missing = resolve_items(names, item_ids)
        missing_all += missing
        if ids:
            blocks.append({
                "type": title,
                "items": [{"id": i, "count": 1} for i in dict.fromkeys(ids)],
                "showIfSummonerSpell": "",
                "hideIfSummonerSpell": "",
            })
    item_set = {
        "title": f"{prefix} {champion}",
        "type": "custom",
        "map": "SR",
        "mode": "any",
        "associatedMaps": [SUMMONERS_RIFT],
        "associatedChampions": [champion_id],
        "blocks": blocks,
        "preferredItemSlots": [],
        "sortrank": 0,
        "startedFrom": "blank",
        "uid": str(uuid.uuid4()),
    }
    return item_set, missing_all


def order_spells(
    names: list[str], spell_ids: dict[str, int], flash_key: str = "D"
) -> tuple[int, int] | None:
    """(D id, F id) with Flash on the configured key; None if a spell is unknown."""
    lookup = {_norm(n): i for n, i in spell_ids.items()}
    ids = [lookup.get(_norm(n)) for n in names[:2]]
    if len(ids) != 2 or not all(ids) or ids[0] == ids[1]:
        return None
    flash = lookup.get("flash")
    if flash in ids:
        other = ids[1] if ids[0] == flash else ids[0]
        return (flash, other) if flash_key.upper() == "D" else (other, flash)
    return ids[0], ids[1]
