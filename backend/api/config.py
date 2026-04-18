"""Shared configuration for the API layer.

All values are overridable via environment variables so deployment tuning
doesn't require a code change.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR") or (Path(tempfile.gettempdir()) / "ats-uploads"))

# How long an uploaded file is retained on disk before it's eligible for
# deletion by the background cleanup task.  Default: 24 hours.
UPLOAD_TTL_SECONDS = _env_int("UPLOAD_TTL_SECONDS", 24 * 60 * 60)

# How often the cleanup task scans UPLOAD_DIR.  Default: every hour.
UPLOAD_CLEANUP_INTERVAL_SECONDS = _env_int("UPLOAD_CLEANUP_INTERVAL_SECONDS", 60 * 60)
