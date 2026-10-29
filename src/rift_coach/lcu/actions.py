"""Write actions against the local League Client.

`connection` is an lcu_driver Connection; `request` returns an aiohttp response.
Only pre-game, client-side actions live here (runes, spells, item sets). Nothing touches
the running game process.
"""

from __future__ import annotations

import logging
from enum import Enum

log = logging.getLogger(__name__)

SESSION = "/lol-champ-select/v1/session"


class RuneImport(Enum):
    IMPORTED = "imported"
    NO_FREE_SLOT = "no_free_slot"
    FAILED = "failed"


async def get_session(connection) -> dict | None:
    resp = await connection.request("get", SESSION)
    return await resp.json() if resp.status == 200 else None


async def get_pickable_ids(connection) -> set[int] | None:
    """Champions the client lets me pick right now (owned / free rotation, not taken)."""
    resp = await connection.request("get", "/lol-champ-select/v1/pickable-champion-ids")
    if resp.status != 200:
        return None
    return set(await resp.json())


async def import_rune_page(
    connection, page: dict, overwrite_current_when_full: bool = False
) -> RuneImport:
    """Writes `page` into the client and selects it.

    Only ever replaces the page named like ours. If every slot is taken by your own pages,
    nothing is deleted unless overwrite_current_when_full is set (then the currently
    selected editable page is replaced, like u.gg / Blitz do).
    """
    pages = await (await connection.request("get", "/lol-perks/v1/pages")).json()
    editable = [p for p in pages if p.get("isEditable")]

    target = next((p for p in editable if p["name"] == page["name"]), None)
    if target is None:
        inventory = await (await connection.request("get", "/lol-perks/v1/inventory")).json()
        full = len(editable) >= inventory.get("ownedPageCount", 0)
        if full:
            current = next((p for p in editable if p.get("current")), None)
            if not (overwrite_current_when_full and current):
                return RuneImport.NO_FREE_SLOT
            target = current
    if target is not None:
        await connection.request("delete", f"/lol-perks/v1/pages/{target['id']}")

    resp = await connection.request("post", "/lol-perks/v1/pages", data=page)
    if resp.status in (200, 201):
        return RuneImport.IMPORTED
    log.warning("Rune import failed: %s %s", resp.status, await resp.text())
    return RuneImport.FAILED


async def set_summoner_spells(connection, spell_d: int, spell_f: int) -> bool:
    """spell1Id is the D key, spell2Id the F key."""
    resp = await connection.request(
        "patch", f"{SESSION}/my-selection", data={"spell1Id": spell_d, "spell2Id": spell_f}
    )
    return resp.status in (200, 204)


async def write_item_set(connection, item_set: dict) -> bool:
    """Adds `item_set` to my item sets, replacing any earlier set with the same title prefix."""
    me = await (await connection.request("get", "/lol-summoner/v1/current-summoner")).json()
    url = f"/lol-item-sets/v1/item-sets/{me['summonerId']}/sets"
    resp = await connection.request("get", url)
    current = await resp.json() if resp.status == 200 else {}

    prefix = item_set["title"].split(" ")[0]
    kept = [s for s in current.get("itemSets", []) if not s.get("title", "").startswith(prefix)]
    body = {
        "accountId": current.get("accountId", me.get("accountId")),
        "itemSets": kept + [item_set],
        "timestamp": current.get("timestamp", 0),
    }
    resp = await connection.request("put", url, data=body)
    if resp.status in (200, 201, 204):
        return True
    log.warning("Item set write failed: %s %s", resp.status, await resp.text())
    return False
