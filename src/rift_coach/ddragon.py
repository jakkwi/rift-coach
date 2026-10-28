"""Data Dragon: Riot's official static game data (champions, runes, items, summoner spells).

Data is downloaded once per patch and cached on disk, so the coach always works with
current names and IDs instead of whatever the model remembers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import httpx

BASE = "https://ddragon.leagueoflegends.com"
SUMMONERS_RIFT_MAP_ID = "11"


@dataclass
class GameData:
    version: str
    champions: dict[int, str]           # champion key (int id) -> display name
    rune_trees: list[dict]              # raw runesReforged.json
    items: list[str]                    # purchasable Summoner's Rift item names
    summoner_spells: dict[str, int]     # spell name -> spell id

    @classmethod
    def from_raw(
        cls, version: str, champion: dict, runes: list, item: dict, summoner: dict
    ) -> GameData:
        champions = {int(c["key"]): c["name"] for c in champion["data"].values()}
        items = sorted(
            {
                it["name"]
                for it in item["data"].values()
                if it.get("gold", {}).get("purchasable")
                and it.get("maps", {}).get(SUMMONERS_RIFT_MAP_ID)
                and not it.get("requiredChampion")
            }
        )
        spells = {
            s["name"]: int(s["key"])
            for s in summoner["data"].values()
            if "CLASSIC" in s.get("modes", [])
        }
        return cls(version, champions, runes, items, spells)

    def champion_name(self, champion_id: int) -> str | None:
        return self.champions.get(champion_id) if champion_id else None

    def rune_names_by_tree(self) -> dict[str, dict[str, list[str]]]:
        """Compact view for the prompt: tree -> {keystones: [...], minor: [...]}."""
        out: dict[str, dict[str, list[str]]] = {}
        for tree in self.rune_trees:
            slots = tree["slots"]
            out[tree["name"]] = {
                "keystones": [r["name"] for r in slots[0]["runes"]],
                "minor": [r["name"] for slot in slots[1:] for r in slot["runes"]],
            }
        return out


class DataDragon:
    def __init__(self, cache_dir: str | Path = ".cache/ddragon", locale: str = "en_US"):
        self.cache_dir = Path(cache_dir)
        self.locale = locale

    def _get_json(self, client: httpx.Client, url: str, cache_file: Path):
        if cache_file.exists():
            return json.loads(cache_file.read_text(encoding="utf-8"))
        resp = client.get(url, timeout=20)
        resp.raise_for_status()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(resp.text, encoding="utf-8")
        return resp.json()

    def load(self) -> GameData:
        with httpx.Client() as client:
            version = client.get(f"{BASE}/api/versions.json", timeout=20).json()[0]
            d = self.cache_dir / version
            cdn = f"{BASE}/cdn/{version}/data/{self.locale}"
            champion = self._get_json(client, f"{cdn}/champion.json", d / "champion.json")
            runes = self._get_json(client, f"{cdn}/runesReforged.json", d / "runes.json")
            item = self._get_json(client, f"{cdn}/item.json", d / "item.json")
            summoner = self._get_json(client, f"{cdn}/summoner.json", d / "summoner.json")
        return GameData.from_raw(version, champion, runes, item, summoner)
