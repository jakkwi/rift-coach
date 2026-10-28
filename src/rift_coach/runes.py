"""Maps a Loadout (rune names) onto an LCU rune page payload (perk IDs)."""

from __future__ import annotations

from .recommender import Loadout

# Stat shards are not in runesReforged.json. IDs as used by the LCU perks API.
# TODO(#issue "Verify stat shard IDs"): confirm against /lol-perks/v1/perks on the current patch.
SHARD_IDS = {
    "offense": {"Adaptive Force": 5008, "Attack Speed": 5005, "Ability Haste": 5007},
    "flex": {"Adaptive Force": 5008, "Move Speed": 5010, "Health Scaling": 5001},
    "defense": {"Health": 5011, "Tenacity and Slow Resist": 5013, "Health Scaling": 5001},
}


class RuneMappingError(ValueError):
    pass


def _norm(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _find_tree(trees: list[dict], name: str) -> dict:
    for tree in trees:
        if _norm(tree["name"]) == _norm(name) or _norm(tree["key"]) == _norm(name):
            return tree
    raise RuneMappingError(f"Unknown rune tree: {name!r}")


def _find_in_slot(slot: dict, name: str) -> int | None:
    for rune in slot["runes"]:
        if _norm(rune["name"]) == _norm(name) or _norm(rune["key"]) == _norm(name):
            return rune["id"]
    return None


def build_rune_page(loadout: Loadout, trees: list[dict], page_name: str) -> dict:
    primary = _find_tree(trees, loadout.primary_tree)
    secondary = _find_tree(trees, loadout.secondary_tree)
    if primary["id"] == secondary["id"]:
        raise RuneMappingError("Primary and secondary tree must differ.")

    keystone = _find_in_slot(primary["slots"][0], loadout.keystone)
    if keystone is None:
        raise RuneMappingError(f"{loadout.keystone!r} is not a keystone of {primary['name']}")

    perk_ids = [keystone]
    for row, name in zip(primary["slots"][1:4], loadout.primary_runes, strict=True):
        rid = _find_in_slot(row, name)
        if rid is None:
            raise RuneMappingError(f"{name!r} does not fit its row in {primary['name']}")
        perk_ids.append(rid)

    used_rows: set[int] = set()
    for name in loadout.secondary_runes:
        for idx, row in enumerate(secondary["slots"][1:4]):
            rid = _find_in_slot(row, name)
            if rid is not None and idx not in used_rows:
                used_rows.add(idx)
                perk_ids.append(rid)
                break
        else:
            raise RuneMappingError(f"{name!r} invalid or duplicates a row in {secondary['name']}")

    for row_name, shard in zip(("offense", "flex", "defense"), loadout.shards, strict=True):
        options = {_norm(k): v for k, v in SHARD_IDS[row_name].items()}
        if _norm(shard) not in options:
            raise RuneMappingError(f"Unknown {row_name} shard: {shard!r}")
        perk_ids.append(options[_norm(shard)])

    return {
        "name": page_name,
        "primaryStyleId": primary["id"],
        "subStyleId": secondary["id"],
        "selectedPerkIds": perk_ids,
        "current": True,
    }
