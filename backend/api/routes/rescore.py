"""Re-score an optimized resume against the same job description."""

from __future__ import annotations

import asyncio
import json
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from src.llm.client import LLMClient
from src.models.ats import ATSScoreReport
from src.observability import Timer, bind_context, get_logger, log_event
from src.scorer.prompts import ATS_SYSTEM_PROMPT, ATS_USER_PROMPT_TEMPLATE

log = get_logger("api.rescore")
router = APIRouter()

LEARNING_SYSTEM_PROMPT = """\
You are a career development advisor. Given an ATS score report and job \
description, suggest specific, actionable skills and topics the candidate \
should learn to become a strong match.

Return a JSON object with this structure:
{
  "learning_suggestions": [
    {
      "skill": "<skill or topic to learn>",
      "priority": "<high|medium|low>",
      "reason": "<why this matters for the role>",
      "resources": "<1-2 concrete learning suggestions, e.g. courses, certs>"
    }
  ]
}

Rules:
1. Focus on the biggest gaps between the resume and JD.
2. Limit to 5-8 suggestions, ordered by impact.
3. Be specific — "Learn Kubernetes" not "improve technical skills".
4. Return raw JSON only."""

LEARNING_USER_TEMPLATE = """\
The candidate scored {score}/100 on ATS matching for this job.

--- SCORE REPORT ---
{report_json}
--- END REPORT ---

--- JOB DESCRIPTION ---
{job_description}
--- END JD ---

Suggest skills and topics they should learn to become a strong match."""


class KeywordChangeItem(BaseModel):
    original: str
    recommended: str
    context: str = ""
    reason: str = ""


class RescoreRequest(BaseModel):
    structured_resume: dict
    keyword_changes: list[KeywordChangeItem]
    jd_text: str
    provider: str | None = None
    model: str | None = None


class LearningSuggestion(BaseModel):
    skill: str
    priority: str = "medium"
    reason: str = ""
    resources: str = ""


class RescoreResponse(BaseModel):
    report: ATSScoreReport
    learning_suggestions: list[LearningSuggestion] = []


@router.post("/rescore", response_model=RescoreResponse)
async def rescore_optimized(req: RescoreRequest):
    if not req.jd_text.strip():
        raise HTTPException(400, "Job description text is required for rescoring.")

    try:
        llm = _build_llm(req.provider, req.model)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    bind_context(provider=llm.provider_name, model=llm.model, route="rescore")
    log_event(log, "rescore.start", change_count=len(req.keyword_changes))

    modified_json = _apply_changes_to_json(req.structured_resume, req.keyword_changes)

    with Timer() as t:
        data = await asyncio.to_thread(
            llm.generate_json,
            ATS_USER_PROMPT_TEMPLATE.format(
                resume_json=json.dumps(modified_json, indent=2),
                job_description=req.jd_text,
            ),
            ATS_SYSTEM_PROMPT,
        )
    log_event(log, "rescore.llm_done", duration_ms=t.duration_ms)

    try:
        report = ATSScoreReport.model_validate(data)
    except ValidationError as exc:
        log_event(
            log, "rescore.validation_failed",
            level=30,  # WARNING
            errors=exc.errors()[:5],
        )
        raise HTTPException(
            422,
            "The LLM returned a malformed report. Try again or switch to a different model.",
        ) from exc
    log_event(log, "rescore.done", overall_score=round(report.overall_score, 1))

    learning: list[LearningSuggestion] = []
    if report.overall_score < 60:
        learning = await _get_learning_suggestions(llm, report, req.jd_text)

    return RescoreResponse(report=report, learning_suggestions=learning)


def _build_llm(provider: str | None, model: str | None) -> LLMClient:
    """Construct an LLMClient from optional request overrides.

    Also used by ``score`` to keep provider construction DRY.  ``ValueError``
    (unknown provider, missing API key) propagates to callers.
    """
    kwargs: dict = {}
    if provider:
        kwargs["provider"] = provider
    if model:
        kwargs["model"] = model
    return LLMClient(**kwargs)


def _apply_changes_to_json(
    resume: dict,
    changes: list[KeywordChangeItem],
) -> dict:
    """Apply keyword substitutions to a structured resume dict."""
    text = json.dumps(resume)
    for change in changes:
        if change.original and change.recommended and change.original != change.recommended:
            text = re.sub(
                re.escape(change.original),
                change.recommended,
                text,
                flags=re.IGNORECASE,
            )
    return json.loads(text)


async def _get_learning_suggestions(
    llm: LLMClient,
    report: ATSScoreReport,
    jd_text: str,
) -> list[LearningSuggestion]:
    """Ask the LLM for targeted learning suggestions when score is low.

    Failures here are non-fatal: the primary rescore result is still useful
    even without learning tips.  We log and return an empty list so the UI
    degrades gracefully.  Caught exceptions are narrowed to what the LLM
    layer and Pydantic actually raise.
    """
    try:
        data = await asyncio.to_thread(
            llm.generate_json,
            LEARNING_USER_TEMPLATE.format(
                score=round(report.overall_score),
                report_json=report.model_dump_json(indent=2),
                job_description=jd_text,
            ),
            LEARNING_SYSTEM_PROMPT,
        )
        items = data.get("learning_suggestions", [])
        return [LearningSuggestion.model_validate(item) for item in items if item]
    except (ValueError, RuntimeError, ConnectionError, ValidationError) as exc:
        log_event(
            log, "rescore.learning_suggestions_failed",
            level=30,  # WARNING
            error=str(exc), exc_type=type(exc).__name__,
        )
        return []
