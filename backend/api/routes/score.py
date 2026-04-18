"""ATS scoring endpoint with Server-Sent Events for progress streaming.

Performance optimisations vs the original:
 - JD resolution and resume parsing run concurrently (asyncio.gather).
 - A single unified LLM call produces both the structured resume and the
   ATS report, eliminating one full round-trip.
"""

from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError
from sse_starlette.sse import EventSourceResponse

from api.routes.rescore import _build_llm
from api.routes.upload import get_file_path
from src.models.ats import ATSScoreReport
from src.models.resume import StructuredResume
from src.observability import bind_context, get_logger, log_event
from src.parsers.factory import ResumeParser
from src.scorer.jd_fetcher import fetch_jd_from_url
from src.scorer.prompts import (
    ATS_SYSTEM_PROMPT,
    ATS_USER_PROMPT_TEMPLATE,
    UNIFIED_SYSTEM_PROMPT,
    UNIFIED_USER_PROMPT_TEMPLATE,
)
from src.structurer.resume_structurer import ResumeStructurer

log = get_logger("api.score")
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
            # ── Step 0: Create LLM client ─────────────────────────────────
            try:
                llm = _build_llm(req.provider, req.model)
            except ValueError as exc:
                log_event(log, "score.llm_init_failed", level=30,
                          error=str(exc), provider=req.provider, model=req.model)
                yield _sse("error", message=str(exc))
                return

            bind_context(
                provider=llm.provider_name,
                model=llm.model,
                file_id=req.file_id,
                route="score",
            )
            log_event(log, "score.start", jd_source="url" if req.jd_url else "text")

            provider_label = f"{llm.provider_name} / {llm.model}"
            yield _sse("progress", step="init",
                       message=f"Using {provider_label}")

            # ── Step 1: Resolve JD + parse resume concurrently ────────────
            yield _sse("progress", step="parsing",
                       message="Extracting resume text and job description...")

            t0 = time.perf_counter()

            if req.jd_url:
                raw_sections, jd_text = await asyncio.gather(
                    asyncio.to_thread(lambda: ResumeParser(str(file_path)).parse()),
                    asyncio.to_thread(fetch_jd_from_url, req.jd_url),
                )
            else:
                jd_text = req.jd_text
                raw_sections = await asyncio.to_thread(
                    lambda: ResumeParser(str(file_path)).parse()
                )

            prep_time = time.perf_counter() - t0
            log_event(
                log, "score.parse_done",
                duration_ms=round(prep_time * 1000, 2),
                section_count=len(raw_sections),
            )
            yield _sse("progress", step="parsing_done",
                       message=f"Ready in {prep_time:.1f}s — {len(raw_sections)} sections extracted")

            resume_text = ResumeStructurer._sections_to_text(raw_sections)

            # ── Step 2: Single unified LLM call ───────────────────────────
            yield _sse("progress", step="analyzing",
                       message=f"Running analysis with {provider_label}...")

            t1 = time.perf_counter()
            data = await asyncio.to_thread(
                llm.generate_json,
                UNIFIED_USER_PROMPT_TEMPLATE.format(
                    resume_text=resume_text,
                    job_description=jd_text,
                ),
                UNIFIED_SYSTEM_PROMPT,
            )
            llm_time = time.perf_counter() - t1
            log_event(
                log, "score.llm_unified_done",
                duration_ms=round(llm_time * 1000, 2),
            )

            yield _sse("progress", step="analyzing_done",
                       message=f"Analysis completed in {llm_time:.1f}s")

            # ── Step 3: Validate — resilient extraction + 2-call fallback ──
            yield _sse("progress", step="validating", message="Validating results...")

            resume_dict, ats_dict = _extract_unified_parts(data)

            try:
                structured_resume = StructuredResume.model_validate(resume_dict)
                report = ATSScoreReport.model_validate(ats_dict)
            except ValidationError as unified_exc:
                # Unified parsing failed (common with smaller local models).
                # Fall back to the original two-call approach silently.
                log_event(
                    log, "score.unified_invalid",
                    level=30,  # WARNING
                    response_keys=list(data.keys()),
                    error_count=len(unified_exc.errors()),
                )
                yield _sse(
                    "progress",
                    step="adapting",
                    message="Adapting for this model — running in compatibility mode...",
                )

                from src.structurer.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

                t_fb = time.perf_counter()

                # Call 1: structure the resume from raw text
                fallback_resume_data = await asyncio.to_thread(
                    llm.generate_json,
                    USER_PROMPT_TEMPLATE.format(resume_text=resume_text),
                    SYSTEM_PROMPT,
                )
                structured_resume = StructuredResume.model_validate(fallback_resume_data)

                # Call 2: ATS score using the structured resume
                fallback_ats_data = await asyncio.to_thread(
                    llm.generate_json,
                    ATS_USER_PROMPT_TEMPLATE.format(
                        resume_json=structured_resume.model_dump_json(indent=2),
                        job_description=jd_text,
                    ),
                    ATS_SYSTEM_PROMPT,
                )
                report = ATSScoreReport.model_validate(fallback_ats_data)

                log_event(
                    log, "score.fallback_done",
                    duration_ms=round((time.perf_counter() - t_fb) * 1000, 2),
                )

            result = {
                "report": json.loads(report.model_dump_json()),
                "structured_resume": json.loads(structured_resume.model_dump_json()),
            }
            log_event(log, "score.complete", overall_score=round(report.overall_score, 1))
            yield _sse("complete", **result)

        except ValidationError as exc:
            log_event(log, "score.validation_failed", level=30, errors=exc.errors()[:5])
            yield _sse("error", message="The LLM returned a malformed report. Try again or switch to a different model.")
        except ValueError as exc:
            log_event(log, "score.value_error", level=30, error=str(exc))
            yield _sse("error", message=str(exc))
        except ConnectionError as exc:
            log_event(log, "score.connection_error", level=30, error=str(exc))
            yield _sse("error", message=f"Connection error: {exc}")
        except RuntimeError as exc:
            log_event(log, "score.runtime_error", level=30, error=str(exc))
            yield _sse("error", message=f"Runtime error: {exc}")
        except Exception as exc:
            log.exception("score.unexpected_error")
            yield _sse("error", message=f"Unexpected error: {exc}")

    return EventSourceResponse(event_generator())


def _sse(event: str, **data) -> dict:
    return {"event": event, "data": json.dumps(data)}


def _extract_unified_parts(data: dict) -> tuple[dict, dict]:
    """Extract structured_resume and ats_report dicts from a raw unified LLM response.

    Local models frequently deviate from the requested envelope.  Three
    strategies are tried in order before giving up and returning empty dicts
    (which will trigger the 2-call fallback in the caller).

    Returns:
        ``(resume_dict, ats_dict)`` — either may be ``{}`` if unrecoverable.
    """
    # Strategy 1: well-formed response — the happy path
    resume_dict: dict = (
        data.get("structured_resume")
        or data.get("resume")
        or data.get("structured")
        or {}
    )
    ats_dict: dict = (
        data.get("ats_report")
        or data.get("ats")
        or data.get("report")
        or data.get("analysis")
        or data.get("ats_score_report")
        or data.get("resume_analysis")
        or {}
    )

    # Strategy 2: flat response — model mixed both parts at the top level.
    # Heuristic: overall_score at root → the whole dict IS the ats_report.
    #            contactInfo at root  → the whole dict IS the structured_resume.
    if not ats_dict and "overall_score" in data:
        ats_dict = data
    if not resume_dict and "contactInfo" in data:
        resume_dict = data

    # Strategy 3: reversed nesting — model put structured_resume inside ats_report.
    if isinstance(ats_dict, dict) and not resume_dict:
        nested = ats_dict.get("structured_resume") or ats_dict.get("resume") or {}
        if nested:
            resume_dict = nested
            ats_dict = {k: v for k, v in ats_dict.items()
                        if k not in ("structured_resume", "resume")}

    return resume_dict, ats_dict
