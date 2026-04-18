"""Tests for the upload-directory TTL cleanup sweep (O9)."""

from __future__ import annotations

import os
import time

from api.services.cleanup import sweep_once


def test_sweep_deletes_old_files(tmp_path):
    recent = tmp_path / "recent.pdf"
    stale = tmp_path / "stale.pdf"
    recent.write_bytes(b"%PDF-fresh")
    stale.write_bytes(b"%PDF-stale")

    # Backdate the stale file by 48 hours
    two_days_ago = time.time() - 48 * 3600
    os.utime(stale, (two_days_ago, two_days_ago))

    deleted, kept = sweep_once(directory=tmp_path, ttl_seconds=24 * 3600)

    assert deleted == 1
    assert kept == 1
    assert recent.exists()
    assert not stale.exists()


def test_sweep_keeps_everything_when_nothing_is_stale(tmp_path):
    fresh = tmp_path / "fresh.pdf"
    fresh.write_bytes(b"%PDF")

    deleted, kept = sweep_once(directory=tmp_path, ttl_seconds=24 * 3600)

    assert deleted == 0
    assert kept == 1
    assert fresh.exists()


def test_sweep_on_missing_directory_is_noop(tmp_path):
    missing = tmp_path / "does-not-exist"
    deleted, kept = sweep_once(directory=missing, ttl_seconds=60)
    assert (deleted, kept) == (0, 0)


def test_sweep_drops_registry_entry(tmp_path, monkeypatch):
    """When a stale file is deleted its registry entry must go with it."""
    from api.routes import upload as upload_module

    file_id = "stale-id-123"
    stale = tmp_path / f"{file_id}.pdf"
    stale.write_bytes(b"%PDF")
    os.utime(stale, (time.time() - 10_000, time.time() - 10_000))

    upload_module._file_registry[file_id] = {
        "filename": "old.pdf",
        "suffix": ".pdf",
        "path": str(stale),
        "page_count": 1,
    }

    sweep_once(directory=tmp_path, ttl_seconds=3600)

    assert not stale.exists()
    assert file_id not in upload_module._file_registry
