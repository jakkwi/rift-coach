import pytest

from rift_coach.recommender import Loadout
from rift_coach.runes import RuneMappingError, build_rune_page


def make_loadout(**overrides) -> Loadout:
    base = dict(
        primary_tree="Domination",
        keystone="Electrocute",
        primary_runes=["Taste of Blood", "Grisly Mementos", "Ultimate Hunter"],
        secondary_tree="Sorcery",
        secondary_runes=["Manaflow Band", "Transcendence"],
        shards=["Adaptive Force", "Adaptive Force", "Health Scaling"],
        summoner_spells=["Flash", "Ignite"],
        starting_items=["Doran's Ring"],
        core_items=[],
    )
    base.update(overrides)
    return Loadout(**base)


def test_builds_valid_page(rune_trees):
    page = build_rune_page(make_loadout(), rune_trees, "RiftCoach")

    assert page["primaryStyleId"] == 8100
    assert page["subStyleId"] == 8200
    assert page["selectedPerkIds"] == [8112, 8139, 8140, 8106, 8226, 8210, 5008, 5008, 5001]
    assert page["current"] is True


def test_name_matching_is_forgiving(rune_trees):
    lo = make_loadout(keystone="electrocute", primary_runes=["taste of blood", "GrislyMementos",
                                                             "Ultimate Hunter"])
    assert build_rune_page(lo, rune_trees, "x")["selectedPerkIds"][0] == 8112


def test_rejects_keystone_from_other_tree(rune_trees):
    with pytest.raises(RuneMappingError):
        build_rune_page(make_loadout(keystone="Arcane Comet"), rune_trees, "x")


def test_rejects_two_secondary_runes_from_same_row(rune_trees):
    lo = make_loadout(secondary_runes=["Transcendence", "Celerity"])
    with pytest.raises(RuneMappingError):
        build_rune_page(lo, rune_trees, "x")


def test_rejects_same_tree_twice(rune_trees):
    with pytest.raises(RuneMappingError):
        build_rune_page(make_loadout(secondary_tree="Domination"), rune_trees, "x")
