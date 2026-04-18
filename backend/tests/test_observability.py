"""Tests for the structured-logging observability layer (O11)."""

from __future__ import annotations

import json
import logging
from io import StringIO

import pytest

from src.observability import (
    Timer,
    bind_context,
    clear_context,
    log_event,
    new_request_id,
    request_id_var,
)
from src.observability.logging import _JsonFormatter


@pytest.fixture
def captured_log():
    """Attach a StringIO-backed JSON handler to a test logger, yield the buffer."""
    buf = StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(_JsonFormatter())
    logger = logging.getLogger("tests.observability")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    yield logger, buf
    logger.handlers.clear()


def _parse(buf: StringIO) -> list[dict]:
    return [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]


def test_log_event_emits_structured_json(captured_log):
    logger, buf = captured_log
    log_event(logger, "test.event", foo="bar", count=3)
    records = _parse(buf)
    assert len(records) == 1
    rec = records[0]
    assert rec["message"] == "test.event"
    assert rec["event"] == "test.event"
    assert rec["foo"] == "bar"
    assert rec["count"] == 3
    assert rec["level"] == "INFO"


def test_request_id_is_injected(captured_log):
    logger, buf = captured_log
    rid = new_request_id()
    log_event(logger, "in.request")
    clear_context()
    log_event(logger, "out.of.request")

    records = _parse(buf)
    assert records[0]["request_id"] == rid
    assert "request_id" not in records[1]


def test_bind_context_merges_fields(captured_log):
    logger, buf = captured_log
    new_request_id()
    bind_context(provider="openai", model="gpt-4o")
    log_event(logger, "llm.call")
    rec = _parse(buf)[0]
    assert rec["provider"] == "openai"
    assert rec["model"] == "gpt-4o"


def test_clear_context_drops_state():
    rid = new_request_id()
    bind_context(provider="x")
    assert request_id_var.get() == rid
    clear_context()
    assert request_id_var.get() is None


def test_timer_reports_positive_duration():
    with Timer() as t:
        sum(i for i in range(1000))
    assert t.duration_ms >= 0
