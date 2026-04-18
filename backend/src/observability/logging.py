"""Structured JSON logging with per-request context.

Adds a ``request_id`` (and optional ``provider`` / ``model`` / ``file_id``) to
every log record produced during a request, so traces can be reconstructed
from log aggregators.  Emits JSON lines to stderr so they're trivially
ingested by tools like Loki, CloudWatch, or jq pipelines.

Usage::

    from src.observability import configure_logging, get_logger, log_event, bind_context

    configure_logging()                       # call once at app startup
    log = get_logger(__name__)

    bind_context(request_id="…", provider="openai")
    log_event(log, "score.start", file_id=file_id)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

# ── Context variables ────────────────────────────────────────────────────────

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_context_var: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})


def new_request_id() -> str:
    """Generate a short request identifier and bind it to the current context."""
    rid = uuid.uuid4().hex[:12]
    request_id_var.set(rid)
    return rid


def bind_context(**fields: Any) -> None:
    """Merge ``fields`` into the current request's log context."""
    current = dict(_context_var.get())
    current.update({k: v for k, v in fields.items() if v is not None})
    _context_var.set(current)


def clear_context() -> None:
    """Reset the log context (call at request boundaries)."""
    _context_var.set({})
    request_id_var.set(None)


def _current_context() -> dict[str, Any]:
    ctx = dict(_context_var.get())
    rid = request_id_var.get()
    if rid and "request_id" not in ctx:
        ctx["request_id"] = rid
    return ctx


# ── Formatter ────────────────────────────────────────────────────────────────


_BASE_KEYS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName",
}


class _JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON with request context merged in."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": round(record.created, 3),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # merge request-scoped context
        for k, v in _current_context().items():
            payload.setdefault(k, v)

        # merge any extra=... fields the caller attached to the record
        for k, v in record.__dict__.items():
            if k in _BASE_KEYS or k.startswith("_"):
                continue
            payload.setdefault(k, v)

        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["exc_message"] = str(record.exc_info[1]) if record.exc_info[1] else None
            payload["traceback"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


# ── Setup ────────────────────────────────────────────────────────────────────


_configured = False


def configure_logging(level: str | None = None, *, json_format: bool | None = None) -> None:
    """Install the JSON handler on the root logger.

    Idempotent — calling twice is a no-op.  Honours ``LOG_LEVEL`` (default
    ``INFO``) and ``LOG_FORMAT`` (``json`` or ``text``; default ``json`` when
    stderr is not a TTY, ``text`` when it is).
    """
    global _configured
    if _configured:
        return

    resolved_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    if json_format is None:
        env_fmt = os.getenv("LOG_FORMAT", "").lower()
        if env_fmt == "json":
            json_format = True
        elif env_fmt == "text":
            json_format = False
        else:
            json_format = not sys.stderr.isatty()

    handler = logging.StreamHandler(sys.stderr)
    if json_format:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))

    root = logging.getLogger()
    # Remove any pre-existing handlers so our format wins (FastAPI/uvicorn also attach).
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(resolved_level)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger; ``configure_logging`` should be called once at startup."""
    return logging.getLogger(name)


# ── Event helper ─────────────────────────────────────────────────────────────


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    """Emit a structured event log.

    ``event`` becomes the message; all keyword args are merged into the JSON
    payload (``extra=``).  ``duration_ms`` / ``duration_s`` is accepted as
    keyword and serialised verbatim.
    """
    logger.log(level, event, extra={"event": event, **fields})


class Timer:
    """Context manager that records elapsed time in ms.

    ::

        with Timer() as t:
            ...
        log_event(log, "parse.done", duration_ms=t.duration_ms)
    """

    def __enter__(self) -> "Timer":
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc: object) -> None:
        self.duration_s = time.perf_counter() - self._t0

    @property
    def duration_ms(self) -> float:
        return round(self.duration_s * 1000, 2)
