"""Shared configuration for the API layer."""

from __future__ import annotations

import tempfile
from pathlib import Path

UPLOAD_DIR = Path(tempfile.gettempdir()) / "ats-uploads"
