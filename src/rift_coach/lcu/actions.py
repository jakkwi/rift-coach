"""Write actions against the local League Client.

`connection` is an lcu_driver Connection; `request` returns an aiohttp response.
Only pre-game, client-side actions live here (runes, spells). Nothing touches the
running game process.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

SESSION = "/lol-champ-select/v1/session"


async def get_session(connection) -> dict | None:
    resp = await connection.request("get", SESSION)
    return await resp.json() if resp.status == 200 else None


async def import_rune_page(connection, page: dict) -> bool:
    """Replaces the page with the same name (or the oldest editable page if slots are full)."""
    resp = await connection.request("get", "/lol-perks/v1/pages")
    pages = await resp.json()
    editable = [p for p in pages if p.get("isEditable")]

    target = next((p for p in editable if p["name"] == page["name"]), None)
    if target is None:
        inventory = await (await connection.request("get", "/lol-perks/v1/inventory")).json()
        if inventory.get("ownedPageCount", 0) <= len(editable) and editable:
            target = editable[-1]
    if target is not None:
        await connection.request("delete", f"/lol-perks/v1/pages/{target['id']}")

    resp = await connection.request("post", "/lol-perks/v1/pages", data=page)
    ok = resp.status in (200, 201)
    if not ok:
        log.warning("Rune import failed: %s %s", resp.status, await resp.text())
    return ok


async def set_summoner_spells(connection, spell1_id: int, spell2_id: int) -> bool:
    resp = await connection.request(
        "patch",
        f"{SESSION}/my-selection",
        data={"spell1Id": spell1_id, "spell2Id": spell2_id},
    )
    return resp.status in (200, 204)
