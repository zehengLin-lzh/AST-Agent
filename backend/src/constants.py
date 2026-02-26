"""Shared constants — section-header patterns, compiled regex, and tuning knobs.

Every module that needs to recognise resume section headers or tweak
layout-detection thresholds imports from here.
"""

from __future__ import annotations

import re

# ── Well-known resume section header patterns ────────────────────────────────

SECTION_PATTERNS: list[str] = [
    r"summary", r"professional\s+summary", r"career\s+summary",
    r"executive\s+summary", r"objective", r"career\s+objective",
    r"profile", r"professional\s+profile", r"about(\s+me)?",
    r"experience", r"work\s+experience", r"professional\s+experience",
    r"employment(\s+history)?", r"work\s+history",
    r"education", r"academic\s+background", r"academic\s+history",
    r"qualifications", r"key\s+qualifications",
    r"skills", r"technical\s+skills", r"core\s+competencies",
    r"competencies", r"areas?\s+of\s+expertise", r"expertise",
    r"certifications?", r"licenses?(\s+and\s+certifications?)?",
    r"certifications?\s+and\s+licenses?",
    r"projects?", r"personal\s+projects?", r"key\s+projects?",
    r"selected\s+projects?",
    r"publications?", r"research(\s+experience)?", r"papers?",
    r"awards?(\s+and\s+honors?)?", r"honors?(\s+and\s+awards?)?",
    r"achievements?", r"accomplishments?",
    r"volunteer(\s+experience)?(\s+work)?", r"community\s+service",
    r"languages?", r"interests?", r"hobbies(\s+and\s+interests?)?",
    r"references?", r"contact(\s+information)?",
    r"personal\s+(information|details?)", r"additional\s+information",
    r"leadership(\s+experience)?", r"(extra-?curricular\s+)?activities",
    r"training(\s+and\s+development)?", r"relevant\s+coursework",
    r"coursework", r"(professional\s+)?affiliations?",
    r"memberships?", r"portfolio", r"strengths?",
]

HEADER_RE = re.compile(
    "|".join(rf"(?:^{p}$)" for p in SECTION_PATTERNS),
    re.IGNORECASE,
)

# ── PDF extraction knobs ─────────────────────────────────────────────────────

BOLD_FLAG = 1 << 4  # bit-4 in PyMuPDF span flags
FULL_WIDTH_RATIO = 0.55  # line wider than this × page_width → "full-width"
COL_MIN_RATIO = 0.15  # min share of lines to count as a column
FONT_HEADER_RATIO = 1.15  # font ≥ median × this → "larger font"
MAX_HEADER_CHARS = 60
MAX_HEADER_WORDS = 6


# ── Helpers ──────────────────────────────────────────────────────────────────


def matches_known_header(text: str) -> bool:
    """Return *True* if *text* matches a well-known resume section name."""
    cleaned = re.sub(r"[:\\-–—|/\\]", " ", text).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return bool(HEADER_RE.match(cleaned))
