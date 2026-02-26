"""ATS scoring pipeline: structured resume + job description → score report.

Pipeline:
    Resume file  ─►  ResumeStructurer  ─►  StructuredResume (JSON)
                                                 │
    JD (text / file / URL)  ─────────────────────┤
                                                 ▼
                                          LLM (ATS analysis)
                                                 │
                                                 ▼
                                         ATSScoreReport
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from src.llm.client import LLMClient
from src.models.ats import ATSScoreReport
from src.models.resume import StructuredResume
from src.scorer.jd_fetcher import fetch_jd_from_url
from src.scorer.prompts import ATS_SYSTEM_PROMPT, ATS_USER_PROMPT_TEMPLATE
from src.structurer.resume_structurer import ResumeStructurer

log = logging.getLogger(__name__)


class ATSScorer:
    """Score a resume against a job description using ATS-style keyword analysis.

    Usage::

        scorer = ATSScorer()
        report = scorer.score("resume.pdf", jd_text="We are looking for …")
        report = scorer.score("resume.pdf", jd_url="https://boards.greenhouse.io/…")
        print(report.model_dump_json(indent=2))
    """

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()
        self._structurer = ResumeStructurer(llm=self.llm)

    def score(
        self,
        resume_path: str | Path,
        *,
        jd_text: str | None = None,
        jd_path: str | Path | None = None,
        jd_url: str | None = None,
    ) -> ATSScoreReport:
        """Run the full ATS scoring pipeline.

        Provide the job description as exactly one of:
        *jd_text* (raw string), *jd_path* (path to a file), or
        *jd_url* (URL to a job posting page).
        """
        job_description = self._resolve_jd(
            jd_text=jd_text, jd_path=jd_path, jd_url=jd_url,
        )

        log.info("Step 1/3 — Structuring resume %s…", Path(resume_path).name)
        t0 = time.perf_counter()
        structured_resume = self._structurer.structure(resume_path)
        log.info("  Resume structured in %.1fs", time.perf_counter() - t0)

        resume_json = structured_resume.model_dump_json(indent=2)

        log.info(
            "Step 2/3 — Running ATS analysis via LLM (%s)…", self.llm.model,
        )
        t1 = time.perf_counter()
        data = self.llm.generate_json(
            prompt=ATS_USER_PROMPT_TEMPLATE.format(
                resume_json=resume_json,
                job_description=job_description,
            ),
            system=ATS_SYSTEM_PROMPT,
        )
        log.info("  ATS analysis completed in %.1fs", time.perf_counter() - t1)

        log.info("Step 3/3 — Validating ATS report…")
        report = ATSScoreReport.model_validate(data)
        log.info(
            "  Score: %.0f/100 | %d keyword changes | %d JD keywords tracked",
            report.overall_score,
            len(report.keyword_changes),
            len(report.jd_keywords),
        )
        return report

    def score_from_structured(
        self,
        structured_resume: StructuredResume,
        *,
        jd_text: str | None = None,
        jd_path: str | Path | None = None,
        jd_url: str | None = None,
    ) -> ATSScoreReport:
        """Score an already-structured resume (skip the parsing stage)."""
        job_description = self._resolve_jd(
            jd_text=jd_text, jd_path=jd_path, jd_url=jd_url,
        )
        resume_json = structured_resume.model_dump_json(indent=2)

        log.info("Running ATS analysis via LLM (%s)…", self.llm.model)
        t0 = time.perf_counter()
        data = self.llm.generate_json(
            prompt=ATS_USER_PROMPT_TEMPLATE.format(
                resume_json=resume_json,
                job_description=job_description,
            ),
            system=ATS_SYSTEM_PROMPT,
        )
        log.info("  ATS analysis completed in %.1fs", time.perf_counter() - t0)

        report = ATSScoreReport.model_validate(data)
        log.info(
            "  Score: %.0f/100 | %d keyword changes | %d JD keywords tracked",
            report.overall_score,
            len(report.keyword_changes),
            len(report.jd_keywords),
        )
        return report

    def score_to_json(
        self,
        resume_path: str | Path,
        *,
        jd_text: str | None = None,
        jd_path: str | Path | None = None,
        jd_url: str | None = None,
        indent: int = 2,
    ) -> str:
        """Convenience wrapper that returns the report as a JSON string."""
        report = self.score(
            resume_path, jd_text=jd_text, jd_path=jd_path, jd_url=jd_url,
        )
        return report.model_dump_json(indent=indent)

    # ── internal ─────────────────────────────────────────────────

    @staticmethod
    def _resolve_jd(
        *,
        jd_text: str | None = None,
        jd_path: str | Path | None = None,
        jd_url: str | None = None,
    ) -> str:
        """Return job description text from exactly one source."""
        sources = sum(1 for s in (jd_text, jd_path, jd_url) if s)
        if sources > 1:
            raise ValueError(
                "Provide exactly one of jd_text, jd_path, or jd_url."
            )
        if jd_url:
            jd_text = fetch_jd_from_url(jd_url)
        elif jd_path:
            p = Path(jd_path)
            if not p.exists():
                raise FileNotFoundError(f"Job description file not found: {p}")
            jd_text = p.read_text(encoding="utf-8").strip()
        if not jd_text:
            raise ValueError(
                "No job description provided. "
                "Pass --jd <file>, --jd-url <url>, or --jd-text '<text>'."
            )
        return jd_text
