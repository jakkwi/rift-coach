from types import SimpleNamespace

import pytest

from rift_coach.llm import LLMError, parse_result


def result(**kw):
    base = dict(is_error=False, structured_output=None, errors=None, result=None,
                subtype="success")
    base.update(kw)
    return SimpleNamespace(**base)


def test_returns_structured_output():
    assert parse_result(result(structured_output={"pick": "Ahri"})) == {"pick": "Ahri"}


def test_error_result_raises():
    with pytest.raises(LLMError, match="rate limited"):
        parse_result(result(is_error=True, errors=["rate limited"]))


def test_missing_result_hints_login():
    with pytest.raises(LLMError, match="login"):
        parse_result(None)


def test_missing_structured_output_raises():
    with pytest.raises(LLMError):
        parse_result(result(result="plain text"))


def test_subscription_backend_disables_session_persistence(monkeypatch):
    import asyncio

    import claude_agent_sdk

    from rift_coach.llm import SubscriptionBackend

    seen = {}

    async def fake_query(prompt, options):
        seen["extra_args"] = options.extra_args
        yield SimpleNamespace(**{})

    monkeypatch.setattr(claude_agent_sdk, "query", fake_query)
    with pytest.raises(LLMError):
        asyncio.run(SubscriptionBackend("m").structured("s", "p", "n", {}))
    assert "no-session-persistence" in seen["extra_args"]
    assert "no-chrome" in seen["extra_args"]
