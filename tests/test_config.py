import pytest

from rift_coach.config import ConfigError, load_config

BASE = '[player]\nrole = "middle"\nchampion_pool = ["Ahri"]\n'


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setattr("rift_coach.config.load_dotenv", lambda: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


def write(tmp_path, extra=""):
    p = tmp_path / "config.toml"
    p.write_text(BASE + extra, encoding="utf-8")
    return p


def test_subscription_needs_no_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = load_config(write(tmp_path, '[claude]\nbackend = "subscription"\n'))
    assert cfg.claude.backend == "subscription"


def test_api_backend_requires_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("rift_coach.config.load_dotenv", lambda: None)
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        load_config(write(tmp_path, '[claude]\nbackend = "api"\n'))


def test_rejects_unknown_backend(tmp_path):
    with pytest.raises(ConfigError, match="backend"):
        load_config(write(tmp_path, '[claude]\nbackend = "magic"\n'))


def test_per_role_pools(tmp_path):
    cfg = load_config(write(tmp_path, '[player.pools]\ntop = ["Garen"]\n'))
    p = cfg.player
    assert p.pool_for("top") == ["Garen"]
    assert p.pool_for("middle") == ["Ahri"]   # legacy champion_pool = pool for `role`
    assert p.pool_for("jungle") == []


def test_role_from_lobby_with_fallback(tmp_path):
    p = load_config(write(tmp_path)).player
    assert p.role_for("top") == "top"
    assert p.role_for("") == "middle"          # blind pick: no assigned position


def test_rejects_unknown_pool_role(tmp_path):
    with pytest.raises(ConfigError, match="mid"):
        load_config(write(tmp_path, '[player.pools]\nmid = ["Ahri"]\n'))
