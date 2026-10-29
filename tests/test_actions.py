import asyncio

from rift_coach.lcu import actions


class Resp:
    def __init__(self, status=200, data=None):
        self.status, self._data = status, data

    async def json(self):
        return self._data

    async def text(self):
        return str(self._data)


class FakeClient:
    def __init__(self, pages, owned, item_sets=None):
        self.pages, self.owned = pages, owned
        self.item_sets = item_sets or {"accountId": 7, "itemSets": [], "timestamp": 1}
        self.calls = []

    async def request(self, method, url, data=None):
        self.calls.append((method, url, data))
        if url == "/lol-perks/v1/pages" and method == "get":
            return Resp(data=self.pages)
        if url == "/lol-perks/v1/inventory":
            return Resp(data={"ownedPageCount": self.owned})
        if url == "/lol-summoner/v1/current-summoner":
            return Resp(data={"summonerId": 42, "accountId": 7})
        if url.endswith("/sets") and method == "get":
            return Resp(data=self.item_sets)
        return Resp(201 if method == "post" else 200)

    def deleted(self):
        return [u for m, u, _ in self.calls if m == "delete"]


PAGE = {"name": "RiftCoach", "selectedPerkIds": []}
MINE = [{"id": 1, "name": "My Ahri", "isEditable": True, "current": True},
        {"id": 2, "name": "My Garen", "isEditable": True, "current": False}]


def run(coro):
    return asyncio.run(coro)


def test_full_slots_never_delete_my_pages():
    c = FakeClient(MINE, owned=2)
    assert run(actions.import_rune_page(c, PAGE)) is actions.RuneImport.NO_FREE_SLOT
    assert c.deleted() == []


def test_reuses_page_with_our_name():
    c = FakeClient(MINE + [{"id": 9, "name": "RiftCoach", "isEditable": True}], owned=3)
    assert run(actions.import_rune_page(c, PAGE)) is actions.RuneImport.IMPORTED
    assert c.deleted() == ["/lol-perks/v1/pages/9"]


def test_free_slot_adds_page():
    c = FakeClient(MINE, owned=5)
    assert run(actions.import_rune_page(c, PAGE)) is actions.RuneImport.IMPORTED
    assert c.deleted() == []


def test_overwrite_current_when_full_opt_in():
    c = FakeClient(MINE, owned=2)
    assert run(actions.import_rune_page(c, PAGE, True)) is actions.RuneImport.IMPORTED
    assert c.deleted() == ["/lol-perks/v1/pages/1"]


def test_item_set_replaces_only_ours():
    existing = {"accountId": 7, "timestamp": 1, "itemSets": [
        {"title": "My own set"}, {"title": "RiftCoach Zed"}]}
    c = FakeClient([], 0, existing)
    assert run(actions.write_item_set(c, {"title": "RiftCoach Ahri"}))
    put = next(d for m, u, d in c.calls if m == "put")
    assert [s["title"] for s in put["itemSets"]] == ["My own set", "RiftCoach Ahri"]
    assert put["accountId"] == 7
