"""Pydantic schema for a fully-structured resume.

Used as the validation target for LLM-extracted data in
:class:`~src.structurer.resume_structurer.ResumeStructurer`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class ContactInfo(BaseModel):
    name: str | None = None
    phoneNumber: str | None = None
    email: str | None = None
    linkedIn: str | None = None
    location: str | None = None
    website: str | None = None
    github: str | None = None


class Experience(BaseModel):
    company: str | None = None
    role: str | None = None
    yearOfService: str | None = Field(
        default=None,
        description="Date range as written, e.g. 'Jan 2020 - Present'",
    )
    location: str | None = None
    highlight: list[str] = []


class Education(BaseModel):
    name: str | None = Field(default=None, description="School / university name")
    degree: str | None = None
    time: str | None = None


class Project(BaseModel):
    name: str | None = None
    description: str | None = None
    technologies: list[str] = []
    time: str | None = None
    highlight: list[str] = []


class Certification(BaseModel):
    name: str | None = None
    issuer: str | None = None
    time: str | None = None


class Award(BaseModel):
    name: str | None = None
    issuer: str | None = None
    time: str | None = None


class StructuredResume(BaseModel):
    """Top-level structured representation of a resume."""

    contactInfo: ContactInfo = Field(default_factory=ContactInfo)
    summary: str | None = None
    experience: list[Experience] = []
    skill: list[str] = []
    education: list[Education] = []
    projects: list[Project] = []
    certifications: list[Certification] = []
    awards: list[Award] = []
    languages: list[str] = []
    additionalSections: dict[str, Any] = Field(
        default_factory=dict,
        description="Catch-all for sections not covered above",
    )

    @model_validator(mode="before")
    @classmethod
    def _sanitize_llm_output(cls, data: Any) -> Any:
        """LLMs sometimes emit `null` for collections; coerce to empty defaults."""
        if isinstance(data, dict):
            for key in ("experience", "skill", "education", "projects",
                        "certifications", "awards", "languages"):
                val = data.get(key)
                if val is None:
                    data[key] = []
                elif isinstance(val, list):
                    data[key] = [item for item in val if item is not None]
            if data.get("additionalSections") is None:
                data["additionalSections"] = {}
        return data
