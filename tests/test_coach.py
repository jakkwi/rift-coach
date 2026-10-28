import asyncio
import copy

from rift_coach.coach import Coach
from rift_coach.config import Config, PlayerConfig
from rift_coach.recommender import Loadout, PickRecommendation

LOADOUT = Loadout("Domination", "Electrocute", ["Taste of Blood", "Grisly Mementos",
                  "Ultimate Hunter"], "Sorcery", ["Manaflow Band", "Transcendence"],
                  ["Adaptive Force", "Adaptive Force", "Health Scaling"], ["Flash", "Ignite"],
                  ["Doran's Ring"], [])


class SlowRecommender:
    """Pick takes a while; loadout is instant. Records what got called."""

    def __init__(self):
        self.picks = 0
        self.loadouts = []

    def role(self, draft):
        return "middle"

    def candidates(self, draft, pickable=None):
        return ["Ahri", "Syndra"], ["Ahri"]

    async def recommend_pick(self, draft, pickable=None):
        self.picks += 1
        await asyncio.sleep(0.2)
        return PickRecommendation("Ahri", [], "r")

    async def recommend_loadout(self, draft, champion):
        self.loadouts.append(champion)
        return LOADOUT


class FakeData:
    rune_trees = []
    summoner_spells = {}

    def __init__(self, champion_name):
        self.champion_name = champion_name


def make_coach(champion_name):
    cfg = Config(player=PlayerConfig(role="middle", champion_pool=["Ahri"]))
    cfg.app.auto_import_runes = False
    rec = SlowRecommender()
    return Coach(cfg, FakeData(champion_name), recommender=rec), rec


def locked(session):
    s = copy.deepcopy(session)
    for group in s["actions"]:
        for a in group:
            if a["actorCellId"] == 2:
                a.update(championId=103, completed=True, isInProgress=False)
    s["myTeam"][2]["championId"] = 103
    return s


def test_lock_cancels_pending_pick_and_starts_loadout(session_my_turn, champion_name, capsys):
    coach, rec = make_coach(champion_name)

    async def scenario():
        await coach.on_session(None, session_my_turn)       # starts pick (slow)
        await asyncio.sleep(0.05)
        await coach.on_session(None, locked(session_my_turn))   # lock while thinking
        await asyncio.sleep(0.3)

    asyncio.run(scenario())
    out = capsys.readouterr().out
    assert rec.loadouts == ["Ahri"]
    assert "Pick" not in out.split("Preparing runes")[-1]   # no pick panel after lock
    assert "alternatives" not in out


def test_hover_spam_does_not_retrigger(session_my_turn, champion_name):
    coach, rec = make_coach(champion_name)

    async def scenario():
        for cid in (222, 412, 157, 222):
            s = copy.deepcopy(session_my_turn)
            s["myTeam"][3]["championPickIntent"] = cid
            await coach.on_session(None, s)
        await asyncio.sleep(0.3)

    asyncio.run(scenario())
    assert rec.picks == 1


def test_stale_events_after_lock_are_ignored(session_my_turn, champion_name):
    coach, rec = make_coach(champion_name)

    async def scenario():
        await coach.on_session(None, locked(session_my_turn))
        stale = copy.deepcopy(session_my_turn)               # older snapshot arriving late
        stale["actions"][2][1].update(championId=222, completed=True, isInProgress=False)
        await coach.on_session(None, locked(stale))
        await asyncio.sleep(0.05)

    asyncio.run(scenario())
    assert rec.picks == 0
    assert rec.loadouts == ["Ahri"]
