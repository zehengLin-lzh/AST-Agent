"""Background task that deletes stale uploaded files.

Files whose mtime is older than ``UPLOAD_TTL_SECONDS`` are removed from
``UPLOAD_DIR`` every ``UPLOAD_CLEANUP_INTERVAL_SECONDS``.  The entry in the
upload registry (if any) is dropped at the same time to avoid serving a
reference to a file that no longer exists on disk.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from api.config import (
    UPLOAD_CLEANUP_INTERVAL_SECONDS,
    UPLOAD_DIR,
    UPLOAD_TTL_SECONDS,
)
from src.observability import get_logger, log_event

log = get_logger("api.cleanup")


def sweep_once(
    directory: Path = UPLOAD_DIR,
    ttl_seconds: int = UPLOAD_TTL_SECONDS,
    *,
    now: float | None = None,
) -> tuple[int, int]:
    """Delete files older than ``ttl_seconds``; return ``(deleted, kept)``.

    Invoked both by the periodic loop and by tests.  Safe to call when the
    directory doesn't exist.
    """
    current = now if now is not None else time.time()
    cutoff = current - ttl_seconds

    if not directory.exists():
        return 0, 0

    deleted = 0
    kept = 0
    for entry in directory.iterdir():
        if not entry.is_file():
            continue
        try:
            mtime = entry.stat().st_mtime
        except FileNotFoundError:
            continue
        if mtime < cutoff:
            try:
                entry.unlink()
            except FileNotFoundError:
                continue
            except OSError as exc:
                log_event(
                    log, "cleanup.delete_failed",
                    path=str(entry), error=str(exc), exc_type=type(exc).__name__,
                )
                kept += 1
                continue

            # Drop the registry entry (imported lazily to avoid a cycle).
            try:
                from api.routes.upload import _file_registry  # noqa: PLC0415
                file_id = entry.stem
                _file_registry.pop(file_id, None)
            except ImportError:
                pass

            deleted += 1
        else:
            kept += 1

    if deleted:
        log_event(log, "cleanup.sweep_done", deleted=deleted, kept=kept)
    return deleted, kept


async def periodic_cleanup(
    interval_seconds: int = UPLOAD_CLEANUP_INTERVAL_SECONDS,
    ttl_seconds: int = UPLOAD_TTL_SECONDS,
    directory: Path = UPLOAD_DIR,
) -> None:
    """Run ``sweep_once`` forever, sleeping ``interval_seconds`` between runs."""
    log_event(
        log, "cleanup.started",
        interval_seconds=interval_seconds, ttl_seconds=ttl_seconds,
        directory=str(directory),
    )
    while True:
        try:
            sweep_once(directory=directory, ttl_seconds=ttl_seconds)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("cleanup.sweep_failed")
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            log_event(log, "cleanup.stopped")
            raise
