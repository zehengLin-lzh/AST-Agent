"""Pydantic schemas for ATS (Applicant Tracking System) scoring reports.

Used as validation targets for the LLM-generated ATS analysis in
:class:`~src.scorer.ats_scorer.ATSScorer`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class KeywordChange(BaseModel):
    """A single 'From → To' keyword replacement recommendation."""

    original: str = Field(description="Current keyword/phrase in the resume")
    recommended: str = Field(
        default="",
        description="Recommended replacement keyword/phrase",
    )
    context: str = Field(
        default="",
        description="The sentence or bullet point where this change applies",
    )
    reason: str = Field(
        default="",
        description="Brief explanation of why this change improves ATS matching",
    )
    impact: str = Field(
        default="medium",
        description="Relative impact on ATS score: high, medium, or low",
    )
    difficulty: str = Field(
        default="easy",
        description="Effort to implement: easy (synonym swap), medium (minor rewrite), hard (skill gap or new section needed)",
    )


class JDKeyword(BaseModel):
    """A keyword extracted from the job description with its match status."""

    keyword: str = Field(description="Keyword or phrase from the job description")
    category: str = Field(
        default="general",
        description="Category: skill, responsibility, qualification, tool, certification, soft_skill",
    )
    found_in_resume: bool = Field(
        default=False,
        description="Whether the keyword (or a close synonym) already exists in the resume",
    )
    added_via_recommendation: bool = Field(
        default=False,
        description="Whether this keyword was incorporated via a From→To recommendation",
    )
    notes: str = Field(
        default="",
        description="Extra context, e.g. where it was found or why it couldn't be added",
    )


class ScoreBreakdown(BaseModel):
    """Category-level sub-scores that feed into the overall match score."""

    skills: float = Field(default=0.0, ge=0, le=100, description="Technical/hard skills match %")
    experience: float = Field(default=0.0, ge=0, le=100, description="Experience/responsibilities match %")
    qualifications: float = Field(default=0.0, ge=0, le=100, description="Education/certifications match %")
    soft_skills: float = Field(default=0.0, ge=0, le=100, description="Soft skills match %")
    tools: float = Field(default=0.0, ge=0, le=100, description="Tools/technologies match %")


class ATSScoreReport(BaseModel):
    """Complete ATS scoring report for a resume against a job description."""

    overall_score: float = Field(
        ge=0, le=100,
        description="Overall ATS match score (0-100)",
    )
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    summary: str = Field(
        default="",
        description="Human-readable summary of the match analysis",
    )
    keyword_changes: list[KeywordChange] = Field(
        default_factory=list,
        description="Recommended From→To keyword substitutions",
    )
    jd_keywords: list[JDKeyword] = Field(
        default_factory=list,
        description="All keywords extracted from the job description with match status",
    )
    missing_critical_keywords: list[str] = Field(
        default_factory=list,
        description="High-impact JD keywords absent from the resume and not addressable via simple swaps",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Resume strengths relative to this JD",
    )
    gaps: list[str] = Field(
        default_factory=list,
        description="Notable gaps between the resume and JD requirements",
    )

    @model_validator(mode="after")
    def filter_incomplete_keyword_changes(self) -> "ATSScoreReport":
        """Drop any keyword_changes where the LLM omitted the recommended field."""
        self.keyword_changes = [
            kc for kc in self.keyword_changes if kc.recommended.strip()
        ]
        return self
