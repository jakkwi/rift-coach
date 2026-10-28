import pytest

from rift_coach.config import ConfigError, load_config

BASE = '[player]\nrole = "middle"\nchampion_pool = ["Ahri"]\n'


def write(tmp_path, extra=""):
    p = tmp_path / "config.toml"
    p.write_text(BASE + extra, encoding="utf-8")
    return p


def test_api_is_default_and_requires_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("rift_coach.config.load_dotenv", lambda: None)
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        load_config(write(tmp_path))


def test_api_backend_reads_key_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    cfg = load_config(write(tmp_path))
    assert cfg.claude.backend == "api"
    assert cfg.anthropic_api_key == "sk-ant-test"


def test_subscription_backend_needs_no_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("rift_coach.config.load_dotenv", lambda: None)
    cfg = load_config(write(tmp_path, '[claude]\nbackend = "subscription"\n'))
    assert cfg.claude.backend == "subscription"


def test_rejects_unknown_backend(tmp_path):
    with pytest.raises(ConfigError, match="backend"):
        load_config(write(tmp_path, '[claude]\nbackend = "magic"\n'))
