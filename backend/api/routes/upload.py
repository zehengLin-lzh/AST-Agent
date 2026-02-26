"""Resume upload and file serving endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path

import fitz  # PyMuPDF
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from api.config import UPLOAD_DIR

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx"}

_file_registry: dict[str, dict] = {}


@router.post("/upload")
async def upload_resume(file: UploadFile):
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format '{suffix}'. Accepted: {', '.join(ALLOWED_EXTENSIONS)}")

    file_id = uuid.uuid4().hex
    dest = UPLOAD_DIR / f"{file_id}{suffix}"
    contents = await file.read()
    dest.write_bytes(contents)

    page_count = 0
    if suffix == ".pdf":
        try:
            doc = fitz.open(str(dest))
            page_count = len(doc)
            doc.close()
        except Exception:
            page_count = 1

    _file_registry[file_id] = {
        "filename": file.filename,
        "suffix": suffix,
        "path": str(dest),
        "page_count": page_count,
    }

    return {
        "file_id": file_id,
        "filename": file.filename,
        "page_count": page_count,
        "file_type": suffix.lstrip("."),
    }


@router.get("/files/{file_id}")
async def get_file(file_id: str):
    info = _file_registry.get(file_id)
    if not info:
        path = _find_file(file_id)
        if not path:
            raise HTTPException(404, "File not found")
        media = "application/pdf" if path.suffix == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return FileResponse(path, media_type=media, filename=path.name)

    path = Path(info["path"])
    if not path.exists():
        raise HTTPException(404, "File not found on disk")

    media = "application/pdf" if info["suffix"] == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(path, media_type=media, filename=info["filename"])


def register_file(file_id: str, filename: str, suffix: str, path: str) -> None:
    """Register a generated file so it can be served via /api/files/{file_id}."""
    _file_registry[file_id] = {
        "filename": filename,
        "suffix": suffix,
        "path": path,
        "page_count": 0,
    }


def get_file_path(file_id: str) -> Path | None:
    """Resolve a file_id to its on-disk Path."""
    info = _file_registry.get(file_id)
    if info:
        p = Path(info["path"])
        return p if p.exists() else None
    return _find_file(file_id)


def _find_file(file_id: str) -> Path | None:
    for ext in ALLOWED_EXTENSIONS:
        p = UPLOAD_DIR / f"{file_id}{ext}"
        if p.exists():
            return p
    return None
