"""Shared fixtures and test configuration.

The backend uses ``src``-rooted imports (``from src.parsers.pdf import ...``)
and ``api``-rooted imports (``from api.main import app``).  Both are resolved
because pytest is invoked from ``backend/`` — which we enforce by placing
this conftest here.
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture
def tmp_upload_dir(tmp_path, monkeypatch):
    """Point UPLOAD_DIR at a temp directory and re-import the registry.

    Ensures tests don't share state with the developer's actual upload dir.
    """
    target = tmp_path / "uploads"
    target.mkdir()
    monkeypatch.setenv("UPLOAD_DIR", str(target))
    # Reload config + upload module so UPLOAD_DIR is re-read from env
    import importlib

    import api.config
    import api.routes.upload
    importlib.reload(api.config)
    importlib.reload(api.routes.upload)
    api.routes.upload._file_registry.clear()
    yield target


@pytest.fixture
def make_pdf_bytes():
    """Factory returning a minimal valid PDF with the given body text."""

    import fitz

    def _make(text: str = "Hello from a test PDF") -> bytes:
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=12)
        buf = io.BytesIO()
        doc.save(buf)
        doc.close()
        return buf.getvalue()

    return _make


@pytest.fixture(autouse=True)
def _reset_log_context():
    """Clear request-scoped log context before each test."""
    from src.observability import clear_context
    clear_context()
    yield
    clear_context()
