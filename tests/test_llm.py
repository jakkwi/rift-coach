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
