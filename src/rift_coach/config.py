"""Loads config.toml and .env into a typed Config object."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

VALID_ROLES = {"top", "jungle", "middle", "bottom", "utility"}
VALID_BACKENDS = {"subscription", "api"}
VALID_SCOPES = {"pool", "viable"}


class ConfigError(Exception):
    pass


@dataclass
class PlayerConfig:
    role: str                                  # fallback when the lobby assigns no position
    champion_pool: list[str] = field(default_factory=list)      # pool for `role`
    pools: dict[str, list[str]] = field(default_factory=dict)   # per-role pools
    # "pool": pick only from your pool. "viable": best pick from every real pick for the role
    # (data/roles.toml), with your pool passed as comfort picks.
    pick_scope: str = "viable"
    riot_id: str = ""
    platform: str = "eun1"
    region: str = "europe"

    def role_for(self, assigned_position: str) -> str:
        return assigned_position if assigned_position in VALID_ROLES else self.role

    def pool_for(self, role: str) -> list[str]:
        if role in self.pools:
            return self.pools[role]
        return self.champion_pool if role == self.role else []


@dataclass
class ClaudeConfig:
    backend: str = "api"   # "api" (API key) or "subscription" (own Claude plan, personal use)
    model: str = "claude-sonnet-5-5"
    max_tokens: int = 1500
    effort: str = "medium"          # subscription backend: low | medium | high
    language: str = "Polish"


@dataclass
class AppConfig:
    auto_import_runes: bool = True
    pick_debounce_s: float = 2.0        # wait for the draft to settle before asking Claude
    rune_page_name: str = "RiftCoach"
    # All rune slots used by your own pages: replace the currently selected one (like u.gg)?
    overwrite_current_page_when_full: bool = False
    auto_set_summoner_spells: bool = True
    flash_key: str = "D"                # "D" or "F"
    auto_item_set: bool = True
    item_set_name: str = "RiftCoach"


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
    player_raw = {**player_raw, "pools": dict(player_raw.get("pools", {}))}
    scope = player_raw.get("pick_scope", "viable")
    if scope not in VALID_SCOPES:
        raise ConfigError(f"player.pick_scope must be one of {sorted(VALID_SCOPES)}")
    if scope == "pool" and not player_raw.get("champion_pool") and not any(
        player_raw["pools"].values()
    ):
        raise ConfigError("pick_scope = \"pool\" needs champion_pool or [player.pools].")

    player = PlayerConfig(**player_raw)
    if player.role not in VALID_ROLES:
        raise ConfigError(f"player.role must be one of {sorted(VALID_ROLES)}, got {player.role!r}")
    flash = str(raw.get("app", {}).get("flash_key", "D")).upper()
    if flash not in {"D", "F"}:
        raise ConfigError("app.flash_key must be \"D\" or \"F\"")
    bad = set(player.pools) - VALID_ROLES
    if bad:
        raise ConfigError(f"Unknown roles in [player.pools]: {sorted(bad)}")

    cfg = Config(
        player=player,
        claude=ClaudeConfig(**raw.get("claude", {})),
        app=AppConfig(**raw.get("app", {})),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        riot_api_key=os.getenv("RIOT_API_KEY", ""),
    )
    if cfg.claude.backend not in VALID_BACKENDS:
        raise ConfigError(f"claude.backend must be one of {sorted(VALID_BACKENDS)}")
    if cfg.claude.backend == "api" and not cfg.anthropic_api_key:
        raise ConfigError("claude.backend = \"api\" needs ANTHROPIC_API_KEY in .env.")
    return cfg
