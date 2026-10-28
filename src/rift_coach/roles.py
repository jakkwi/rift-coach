"""Per-role list of viable champions (data/roles.toml), resolved against Data Dragon names."""

from __future__ import annotations

import logging
import tomllib
from importlib.resources import files

log = logging.getLogger(__name__)


def _norm(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def load_viable(
    known_names: list[str] | None = None, text: str | None = None
) -> dict[str, list[str]]:
    """Role -> champion names. With known_names (Data Dragon), names are canonicalised and
    entries that don't exist on the current patch are dropped with a warning."""
    if text is None:
        text = files("rift_coach").joinpath("data/roles.toml").read_text(encoding="utf-8")
    raw = tomllib.loads(text)
    if known_names is None:
        return {role: list(names) for role, names in raw.items()}

    canonical = {_norm(n): n for n in known_names}
    out: dict[str, list[str]] = {}
    for role, names in raw.items():
        resolved = []
        for name in names:
            hit = canonical.get(_norm(name))
            if hit:
                resolved.append(hit)
            else:
                log.warning("roles.toml: %r (%s) not found in Data Dragon, skipped", name, role)
        out[role] = resolved
    return out
