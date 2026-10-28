import pytest

from rift_coach.recommender import validate_pick

POOL = ["Ahri", "Orianna", "Syndra"]


def test_accepts_pick_from_pool():
    rec = validate_pick({"pick": "syndra", "alternatives": ["Ahri"], "reasoning": "r"}, POOL, set())
    assert rec.pick == "Syndra"
    assert rec.alternatives == ["Ahri"]
    assert rec.corrected is False


def test_corrects_pick_outside_pool():
    rec = validate_pick({"pick": "Swain", "alternatives": ["Orianna"], "reasoning": "r"}, POOL,
                        set())
    assert rec.pick == "Orianna"
    assert rec.corrected is True


def test_skips_banned_champions():
    rec = validate_pick({"pick": "Ahri", "alternatives": [], "reasoning": "r"}, POOL,
                        {"Ahri", "Orianna"})
    assert rec.pick == "Syndra"
    assert rec.corrected is True


def test_whole_pool_unavailable():
    with pytest.raises(ValueError):
        validate_pick({"pick": "Ahri", "alternatives": []}, POOL, set(POOL))
