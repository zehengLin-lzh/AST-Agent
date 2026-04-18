"""Tests for the resilient unified-response extraction in score.py.

``_extract_unified_parts`` is the core of the graceful-degradation story
when smaller LLMs emit flat or reversed response shapes.  Each strategy
is exercised explicitly.
"""

from __future__ import annotations

from api.routes.score import _extract_unified_parts


def test_happy_path_well_formed():
    data = {
        "structured_resume": {"contactInfo": {"name": "A"}},
        "ats_report": {"overall_score": 80},
    }
    resume, ats = _extract_unified_parts(data)
    assert resume == {"contactInfo": {"name": "A"}}
    assert ats == {"overall_score": 80}


def test_alternate_top_level_keys():
    data = {
        "resume": {"contactInfo": {"name": "B"}},
        "analysis": {"overall_score": 65},
    }
    resume, ats = _extract_unified_parts(data)
    assert resume["contactInfo"]["name"] == "B"
    assert ats["overall_score"] == 65


def test_flat_ats_at_root():
    """Model forgot the envelope and put the ATS report at the top level."""
    data = {"overall_score": 42, "skills": ["python"]}
    resume, ats = _extract_unified_parts(data)
    assert ats["overall_score"] == 42
    assert resume == {}


def test_flat_resume_at_root():
    data = {"contactInfo": {"name": "C"}, "education": []}
    resume, ats = _extract_unified_parts(data)
    assert resume["contactInfo"]["name"] == "C"
    assert ats == {}


def test_reversed_nesting_resume_inside_ats():
    """Model nested structured_resume inside ats_report."""
    data = {
        "ats_report": {
            "overall_score": 70,
            "structured_resume": {"contactInfo": {"name": "D"}},
        }
    }
    resume, ats = _extract_unified_parts(data)
    assert resume["contactInfo"]["name"] == "D"
    assert ats == {"overall_score": 70}
    assert "structured_resume" not in ats


def test_empty_payload_returns_empty_dicts():
    resume, ats = _extract_unified_parts({})
    assert resume == {}
    assert ats == {}
