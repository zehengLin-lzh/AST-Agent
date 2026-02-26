"""Generate an optimized resume PDF based on ATS suggestions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.routes.upload import get_file_path, register_file
from api.services.resume_generator import generate_optimized_resume

router = APIRouter()


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

    changes = [kc.model_dump() for kc in req.keyword_changes]

    try:
        output_path = generate_optimized_resume(str(source_path), changes)
    except Exception as exc:
        raise HTTPException(500, f"Failed to generate resume: {exc}") from exc

    gen_file_id = uuid.uuid4().hex
    register_file(gen_file_id, "optimized_resume.pdf", ".pdf", output_path)

    return {"file_id": gen_file_id}
