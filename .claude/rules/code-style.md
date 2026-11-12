---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
---
# Python code style

- Python 3.11+, type hints on public functions, ruff rules from pyproject.toml (line length 100).
- Boundaries: `lcu/` is the only code that talks to the League Client, `llm.py` the only code that calls Claude, `ddragon.py` the only code that fetches Data Dragon. Other modules get data passed in.
- Recommendation logic (`recommender.py`, `runes.py`, `itemset.py`, `roles.py`) stays pure and testable without the client or the network.
- Logging via `rich`/logging, never secrets or the LCU auth token.
- Windows is the target: `pathlib`, no shell-specific commands.
