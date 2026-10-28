"""Loads config.toml and .env into a typed Config object."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

VALID_ROLES = {"top", "jungle", "middle", "bottom", "utility"}


class ConfigError(Exception):
    pass


@dataclass
class PlayerConfig:
    role: str
    champion_pool: list[str]
    riot_id: str = ""
    platform: str = "eun1"
    region: str = "europe"


@dataclass
class ClaudeConfig:
    model: str = "claude-sonnet-5-5"
    max_tokens: int = 1500
    language: str = "Polish"


@dataclass
class AppConfig:
    auto_import_runes: bool = True
    auto_set_summoner_spells: bool = False
    rune_page_name: str = "RiftCoach"


@dataclass
class Config:
    player: PlayerConfig
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    app: AppConfig = field(default_factory=AppConfig)
    anthropic_api_key: str = ""
    riot_api_key: str = ""


def load_config(path: str | Path = "config.toml") -> Config:
    load_dotenv()
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"{path} not found. Copy config.example.toml to {path} first.")

    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    player_raw = raw.get("player", {})
    if not player_raw.get("champion_pool"):
        raise ConfigError("player.champion_pool must contain at least one champion.")

    player = PlayerConfig(**player_raw)
    if player.role not in VALID_ROLES:
        raise ConfigError(f"player.role must be one of {sorted(VALID_ROLES)}, got {player.role!r}")

    cfg = Config(
        player=player,
        claude=ClaudeConfig(**raw.get("claude", {})),
        app=AppConfig(**raw.get("app", {})),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        riot_api_key=os.getenv("RIOT_API_KEY", ""),
    )
    if not cfg.anthropic_api_key:
        raise ConfigError("ANTHROPIC_API_KEY is missing. Put it in .env.")
    return cfg
