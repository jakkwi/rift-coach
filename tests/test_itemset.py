from rift_coach.itemset import build_item_set, order_spells, resolve_items
from rift_coach.recommender import Loadout

ITEMS = {"Doran's Ring": "1056", "Health Potion": "2003", "Luden's Companion": "6655",
         "Sorcerer's Shoes": "3020", "Zhonya's Hourglass": "3157", "Banshee's Veil": "3102"}
SPELLS = {"Flash": 4, "Ignite": 14, "Teleport": 12, "Smite": 11}


def loadout(**kw):
    base = dict(primary_tree="Domination", keystone="Electrocute", primary_runes=[],
                secondary_tree="Sorcery", secondary_runes=[], shards=[],
                summoner_spells=["Ignite", "Flash"],
                starting_items=["Doran's Ring", "Health Potion", "Health Potion"],
                core_items=["Luden's Companion", "Sorcerer's Shoes", "Zhonya's Hourglass"],
                situational=[{"item": "Banshee's Veil", "when": "vs burst"},
                             {"item": "Old Removed Item", "when": "never"}])
    base.update(kw)
    return Loadout(**base)


def test_item_set_blocks_and_missing():
    item_set, missing = build_item_set(loadout(), "Ahri", 103, ITEMS, "RiftCoach")
    assert item_set["title"] == "RiftCoach Ahri"
    assert item_set["associatedChampions"] == [103]
    assert [b["type"] for b in item_set["blocks"]] == ["Start", "Core (in order)", "Situational"]
    assert [i["id"] for i in item_set["blocks"][0]["items"]] == ["1056", "2003"]  # deduped
    assert missing == ["Old Removed Item"]


def test_resolve_is_forgiving():
    ids, missing = resolve_items(["ludens companion", "ZHONYA'S HOURGLASS"], ITEMS)
    assert ids == ["6655", "3157"] and missing == []


def test_flash_goes_on_configured_key():
    assert order_spells(["Ignite", "Flash"], SPELLS, "D") == (4, 14)
    assert order_spells(["Flash", "Ignite"], SPELLS, "F") == (14, 4)


def test_no_flash_keeps_order_and_rejects_bad():
    assert order_spells(["Smite", "Teleport"], SPELLS) == (11, 12)
    assert order_spells(["Flash", "Flash"], SPELLS) is None
    assert order_spells(["Flash", "Ghostz"], SPELLS) is None
