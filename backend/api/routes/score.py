"""ATS scoring endpoint with Server-Sent Events for progress streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from api.routes.upload import get_file_path
from src.llm.client import LLMClient
from src.models.ats import ATSScoreReport
from src.parsers.factory import ResumeParser
from src.scorer.jd_fetcher import fetch_jd_from_url
from src.scorer.prompts import ATS_SYSTEM_PROMPT, ATS_USER_PROMPT_TEMPLATE
from src.structurer.resume_structurer import ResumeStructurer

log = logging.getLogger(__name__)
router = APIRouter()


class ScoreRequest(BaseModel):
    file_id: str
    jd_text: str | None = None
    jd_url: str | None = None
    provider: str | None = None
    model: str | None = None


@router.post("/score")
async def score_resume(req: ScoreRequest):
    file_path = get_file_path(req.file_id)
    if not file_path:
        raise HTTPException(404, "Resume file not found. Please upload again.")

    if not req.jd_text and not req.jd_url:
        raise HTTPException(400, "Provide either jd_text or jd_url")

    async def event_generator():
        try:
            # Step 0: Create LLM client with selected provider/model
            llm_kwargs: dict = {}
            if req.provider:
                llm_kwargs["provider"] = req.provider
            if req.model:
                llm_kwargs["model"] = req.model

            try:
                llm = LLMClient(**llm_kwargs)
            except ValueError as exc:
                yield _sse("error", message=str(exc))
                return

            provider_label = f"{llm.provider_name} / {llm.model}"
            yield _sse("progress", step="init",
                        message=f"Using {provider_label}")

            # Step 1: Resolve JD
            yield _sse("progress", step="resolving_jd", message="Resolving job description...")

            if req.jd_url:
                jd_text = await asyncio.to_thread(fetch_jd_from_url, req.jd_url)
            else:
                jd_text = req.jd_text

            yield _sse("progress", step="resolving_jd_done", message="Job description ready")

            # Step 2: Parse resume
            yield _sse("progress", step="parsing", message="Extracting text from resume...")

            t0 = time.perf_counter()
            raw_sections = await asyncio.to_thread(
                lambda: ResumeParser(str(file_path)).parse()
            )
            parse_time = time.perf_counter() - t0

            yield _sse("progress", step="parsing_done",
                        message=f"Extracted {len(raw_sections)} sections in {parse_time:.1f}s")

            # Step 3: Structure with LLM
            yield _sse("progress", step="structuring",
                        message=f"Structuring resume with {provider_label}...")

            structurer = ResumeStructurer(llm=llm)
            t1 = time.perf_counter()
            structured_resume = await asyncio.to_thread(structurer.structure, str(file_path))
            structure_time = time.perf_counter() - t1

            yield _sse("progress", step="structuring_done",
                        message=f"Resume structured in {structure_time:.1f}s")

            resume_json = structured_resume.model_dump_json(indent=2)

            # Step 4: ATS scoring
            yield _sse("progress", step="scoring",
                        message=f"Running ATS analysis with {provider_label}...")

            t2 = time.perf_counter()
            data = await asyncio.to_thread(
                llm.generate_json,
                ATS_USER_PROMPT_TEMPLATE.format(
                    resume_json=resume_json,
                    job_description=jd_text,
                ),
                ATS_SYSTEM_PROMPT,
            )
            score_time = time.perf_counter() - t2

            yield _sse("progress", step="scoring_done",
                        message=f"ATS analysis completed in {score_time:.1f}s")

            # Step 5: Validate and return
            yield _sse("progress", step="validating", message="Validating results...")

            report = ATSScoreReport.model_validate(data)

            result = {
                "report": json.loads(report.model_dump_json()),
                "structured_resume": json.loads(resume_json),
            }
            yield _sse("complete", **result)

        except ValueError as exc:
            yield _sse("error", message=str(exc))
        except ConnectionError as exc:
            yield _sse("error", message=f"Connection error: {exc}")
        except RuntimeError as exc:
            yield _sse("error", message=f"Runtime error: {exc}")
        except Exception as exc:
            log.exception("Unexpected error during scoring")
            yield _sse("error", message=f"Unexpected error: {exc}")

    return EventSourceResponse(event_generator())


def _sse(event: str, **data) -> dict:
    return {"event": event, "data": json.dumps(data)}
