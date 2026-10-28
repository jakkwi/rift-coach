import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def champion_name():
    champs = {int(k): v for k, v in load("champions.json").items()}
    return lambda cid: champs.get(cid) if cid else None


@pytest.fixture
def session_my_turn():
    return load("session_my_turn.json")


@pytest.fixture
def rune_trees():
    return load("runes_subset.json")
