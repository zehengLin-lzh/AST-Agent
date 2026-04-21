"""Generate an optimized resume PDF based on ATS suggestions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.routes.upload import get_file_path, register_file
from api.services.resume_generator import generate_optimized_resume
from src.observability import bind_context, get_logger, log_event

log = get_logger("api.generate")
router = APIRouter()

# Failure modes we expect from the generator stack (PyMuPDF + python-docx):
#   * ValueError      — unsupported file format from generate_optimized_resume
#   * RuntimeError    — PyMuPDF (fitz.FileDataError, layout errors)
#   * OSError         — I/O on UPLOAD_DIR / temp files
#   * KeyError        — malformed change dicts (missing original/recommended)
_GENERATOR_RECOVERABLE = (ValueError, RuntimeError, OSError, KeyError)


class KeywordChange(BaseModel):
    original: str
    recommended: str
    context: str = ""
    reason: str = ""


class GenerateRequest(BaseModel):
    file_id: str
    keyword_changes: list[KeywordChange]


@router.post("/generate-resume")
async def generate_resume(req: GenerateRequest):
    source_path = get_file_path(req.file_id)
    if not source_path:
        raise HTTPException(404, "Original resume not found. Please upload again.")

    bind_context(file_id=req.file_id, route="generate")
    changes = [kc.model_dump() for kc in req.keyword_changes]

    try:
        output_path = generate_optimized_resume(str(source_path), changes)
    except _GENERATOR_RECOVERABLE as exc:
        log_event(
            log, "generate.failed",
            level=30,  # WARNING
            error=str(exc), exc_type=type(exc).__name__,
            change_count=len(changes),
        )
        raise HTTPException(500, f"Failed to generate resume: {exc}") from exc

    gen_file_id = uuid.uuid4().hex
    register_file(gen_file_id, "optimized_resume.pdf", ".pdf", output_path)
    log_event(
        log, "generate.success",
        gen_file_id=gen_file_id, change_count=len(changes),
    )

    return {"file_id": gen_file_id}
