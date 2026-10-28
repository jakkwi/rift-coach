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


def test_no_pool_for_assigned_role(session_my_turn, champion_name):
    import asyncio

    from rift_coach.champselect import parse_session
    from rift_coach.config import Config, PlayerConfig
    from rift_coach.recommender import NoPoolError, Recommender

    class Boom:
        async def structured(self, *a, **k):
            raise AssertionError("must not call Claude without a pool")

    cfg = Config(player=PlayerConfig(role="middle", champion_pool=POOL, pick_scope="pool"))
    draft = parse_session(session_my_turn, champion_name)
    draft.my_position = "top"
    rec = Recommender(cfg, data=None, backend=Boom())
    with pytest.raises(NoPoolError):
        asyncio.run(rec.recommend_pick(draft))


def _rec(scope, pools=None):
    from rift_coach.config import Config, PlayerConfig
    from rift_coach.recommender import Recommender

    cfg = Config(player=PlayerConfig(role="middle", pools=pools or {"middle": POOL},
                                     pick_scope=scope))
    return Recommender(cfg, data=None, backend=object())


def test_viable_scope_uses_role_list_plus_comfort(session_my_turn, champion_name):
    from rift_coach.champselect import parse_session

    draft = parse_session(session_my_turn, champion_name)
    draft.my_position = "top"
    cands, comfort = _rec("viable", {"top": ["Garen"]}).candidates(draft)
    assert "Aatrox" in cands and "Swain" not in cands
    assert "Garen" not in cands          # already locked by an ally in the fixture
    assert comfort == ["Garen"]


def test_pickable_filter(session_my_turn, champion_name):
    from rift_coach.champselect import parse_session

    draft = parse_session(session_my_turn, champion_name)   # middle
    cands, _ = _rec("viable").candidates(draft, pickable={"Ahri", "Syndra", "Zed"})
    assert cands == ["Ahri", "Syndra"]   # Zed is enemy, Orianna banned / not owned


def test_pool_scope_only_pool(session_my_turn, champion_name):
    from rift_coach.champselect import parse_session

    draft = parse_session(session_my_turn, champion_name)
    cands, _ = _rec("pool").candidates(draft)
    assert cands == ["Ahri", "Syndra"]   # Orianna is banned
