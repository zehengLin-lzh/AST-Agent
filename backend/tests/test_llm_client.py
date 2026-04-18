"""Tests for LLMClient wiring and helpers.

Network calls are NOT exercised — we verify provider dispatch, config
validation, and the JSON extraction helper that normalises LLM output.
"""

from __future__ import annotations

import json

import pytest

from src.llm.client import LLMClient, PROVIDERS, _extract_json, get_providers_info


def test_unknown_provider_raises(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    with pytest.raises(ValueError, match="Unknown provider"):
        LLMClient(provider="does-not-exist")


def test_openai_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        LLMClient(provider="openai")


def test_local_provider_defaults_work_without_api_key(monkeypatch):
    """Local (Ollama) has no env_key, so it should construct with defaults."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = LLMClient(provider="local")
    assert client.provider_name == "local"
    assert client.model == PROVIDERS["local"].default_model


def test_provider_info_reports_configured_state(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    info = {p["id"]: p for p in get_providers_info()}
    assert info["local"]["configured"] is True  # no key needed
    assert info["openai"]["configured"] is False
    assert info["anthropic"]["configured"] is True


@pytest.mark.parametrize("raw,expected", [
    ('{"a": 1}', {"a": 1}),
    ('```json\n{"b": 2}\n```', {"b": 2}),
    ('```\n{"c": 3}\n```', {"c": 3}),
    ('  prose before\n{"d": 4}\n', None),  # _extract_json only strips fences
])
def test_extract_json_handles_fences(raw, expected):
    extracted = _extract_json(raw)
    if expected is None:
        # without fences _extract_json returns text as-is; json.loads may fail
        assert extracted.strip() == raw.strip()
    else:
        assert json.loads(extracted) == expected
