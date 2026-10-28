"""Asks Claude for a pick and a loadout, using forced tool calls for structured output.

The model only reasons; facts (champion names, runes, items for the current patch)
come from Data Dragon and are passed in the prompt. Picks are validated against
the configured champion pool, so the coach cannot suggest a champion you don't play.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from anthropic import AsyncAnthropic

from .champselect import DraftState
from .config import Config
from .ddragon import GameData

SHARD_OPTIONS = {
    "offense": ["Adaptive Force", "Attack Speed", "Ability Haste"],
    "flex": ["Adaptive Force", "Move Speed", "Health Scaling"],
    "defense": ["Health", "Tenacity and Slow Resist", "Health Scaling"],
}

PICK_TOOL = {
    "name": "submit_pick",
    "description": "Submit the recommended champion pick for this draft.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pick": {"type": "string", "description": "Champion from the player's pool."},
            "alternatives": {"type": "array", "items": {"type": "string"}, "maxItems": 2},
            "reasoning": {"type": "string", "description": "2-4 sentences: why this pick here."},
        },
        "required": ["pick", "alternatives", "reasoning"],
    },
}

LOADOUT_TOOL = {
    "name": "submit_loadout",
    "description": "Submit runes, summoner spells and build for the locked champion.",
    "input_schema": {
        "type": "object",
        "properties": {
            "primary_tree": {"type": "string"},
            "keystone": {"type": "string"},
            "primary_runes": {"type": "array", "items": {"type": "string"}, "minItems": 3,
                              "maxItems": 3, "description": "One rune per row, rows 1-3."},
            "secondary_tree": {"type": "string"},
            "secondary_runes": {"type": "array", "items": {"type": "string"}, "minItems": 2,
                                "maxItems": 2, "description": "From two different rows."},
            "shards": {"type": "array", "items": {"type": "string"}, "minItems": 3,
                       "maxItems": 3, "description": "Offense, flex, defense in that order."},
            "summoner_spells": {"type": "array", "items": {"type": "string"}, "minItems": 2,
                                "maxItems": 2},
            "starting_items": {"type": "array", "items": {"type": "string"}},
            "core_items": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
            "situational": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"item": {"type": "string"}, "when": {"type": "string"}},
                    "required": ["item", "when"],
                },
            },
            "matchup_tips": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
            "reasoning": {"type": "string"},
        },
        "required": ["primary_tree", "keystone", "primary_runes", "secondary_tree",
                     "secondary_runes", "shards", "summoner_spells", "starting_items",
                     "core_items", "situational", "matchup_tips", "reasoning"],
    },
}


@dataclass
class PickRecommendation:
    pick: str
    alternatives: list[str]
    reasoning: str
    corrected: bool = False   # True if the model suggested something outside the pool


@dataclass
class Loadout:
    primary_tree: str
    keystone: str
    primary_runes: list[str]
    secondary_tree: str
    secondary_runes: list[str]
    shards: list[str]
    summoner_spells: list[str]
    starting_items: list[str]
    core_items: list[str]
    situational: list[dict] = field(default_factory=list)
    matchup_tips: list[str] = field(default_factory=list)
    reasoning: str = ""


def _draft_payload(draft: DraftState) -> dict:
    d = asdict(draft)
    d.pop("my_turn_to_pick", None)
    return d


def validate_pick(rec: dict, pool: list[str], unavailable: set[str]) -> PickRecommendation:
    available = [c for c in pool if c not in unavailable]
    lookup = {c.lower(): c for c in available}
    pick = lookup.get(str(rec.get("pick", "")).lower())
    alternatives = [lookup[a.lower()] for a in rec.get("alternatives", []) if a.lower() in lookup]
    alternatives = [a for a in alternatives if a != pick]
    corrected = pick is None
    if corrected:
        if not available:
            raise ValueError("Every champion in your pool is banned or taken.")
        pick = alternatives.pop(0) if alternatives else available[0]
    return PickRecommendation(pick, alternatives, rec.get("reasoning", ""), corrected)


class Recommender:
    def __init__(self, cfg: Config, data: GameData):
        self.cfg = cfg
        self.data = data
        self.client = AsyncAnthropic(api_key=cfg.anthropic_api_key)

    def _system(self) -> str:
        return (
            "You are a high-elo League of Legends coach helping one player in champ select. "
            f"Current patch: {self.data.version}. Use only names given in the data provided; "
            "do not rely on remembered item or rune names, they may be outdated. "
            "Prefer champions the player knows well over statistically trendy picks. "
            f"Write all free-text fields in {self.cfg.claude.language}, concise, teaching the "
            "reason behind each choice."
        )

    async def _call_tool(self, tool: dict, user_content: str) -> dict:
        msg = await self.client.messages.create(
            model=self.cfg.claude.model,
            max_tokens=self.cfg.claude.max_tokens,
            system=self._system(),
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": user_content}],
        )
        for block in msg.content:
            if block.type == "tool_use":
                return block.input
        raise RuntimeError("Model did not return a tool call.")

    async def recommend_pick(self, draft: DraftState) -> PickRecommendation:
        pool = self.cfg.player.champion_pool
        prompt = json.dumps(
            {
                "task": "Pick the best champion for me from my pool in this draft.",
                "my_role": self.cfg.player.role,
                "my_pool": pool,
                "unavailable": sorted(draft.unavailable()),
                "draft": _draft_payload(draft),
            },
            ensure_ascii=False,
            indent=2,
        )
        raw = await self._call_tool(PICK_TOOL, prompt)
        return validate_pick(raw, pool, draft.unavailable())

    async def recommend_loadout(self, draft: DraftState, champion: str) -> Loadout:
        prompt = json.dumps(
            {
                "task": f"I locked {champion}. Give runes, summoner spells and build.",
                "my_role": self.cfg.player.role,
                "draft": _draft_payload(draft),
                "rune_trees": self.data.rune_names_by_tree(),
                "shard_options": SHARD_OPTIONS,
                "summoner_spells": sorted(self.data.summoner_spells),
                "items": self.data.items,
            },
            ensure_ascii=False,
            indent=2,
        )
        raw = await self._call_tool(LOADOUT_TOOL, prompt)
        return Loadout(**raw)
