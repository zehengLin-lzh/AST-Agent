"""End-to-end integration tests with the LLM layer mocked.

These tests exercise the full SSE scoring pipeline and rescore endpoint —
parser → prompt assembly → LLM dispatch → Pydantic validation → response
construction — without any network or Ollama dependency.  Failures here
indicate a contract break between the route handlers and the models,
which unit tests cannot catch.
"""

from __future__ import annotations

import io
import json

import fitz
import pytest
from fastapi.testclient import TestClient


UNIFIED_PAYLOAD = {
    "structured_resume": {
        "contactInfo": {"name": "Jane Doe", "email": "jane@example.com"},
        "summary": "Senior software engineer.",
        "experience": [
            {
                "company": "Acme",
                "role": "SWE",
                "yearOfService": "2020 - 2024",
                "highlight": ["Built a thing"],
            }
        ],
        "skill": ["Python", "AWS"],
        "education": [],
        "projects": [],
        "certifications": [],
        "awards": [],
        "languages": [],
    },
    "ats_report": {
        "overall_score": 78.5,
        "score_breakdown": {
            "skills": 80, "experience": 75, "qualifications": 70,
            "soft_skills": 60, "tools": 90,
        },
        "summary": "Strong technical match with minor gaps.",
        "keyword_changes": [
            {
                "original": "Built a thing",
                "recommended": "Architected a distributed system",
                "impact": "high",
                "difficulty": "easy",
                "reason": "Stronger verb aligns with JD.",
            }
        ],
        "jd_keywords": [],
        "missing_critical_keywords": [],
        "strengths": ["Python expertise", "AWS hands-on"],
        "gaps": ["No Kubernetes experience"],
    },
}


RESCORE_PAYLOAD = {
    "overall_score": 88.0,
    "score_breakdown": {
        "skills": 90, "experience": 85, "qualifications": 80,
        "soft_skills": 70, "tools": 95,
    },
    "summary": "Score improved after optimization.",
    "keyword_changes": [],
    "jd_keywords": [],
    "missing_critical_keywords": [],
    "strengths": ["Python", "AWS"],
    "gaps": [],
}


@pytest.fixture
def mock_llm(monkeypatch):
    """Monkey-patch LLMClient so no network calls happen."""
    responses: list[dict] = []

    def generate_json(self, prompt, system=None):  # bound method replacement
        return responses.pop(0) if responses else {}

    from src.llm.client import LLMClient
    monkeypatch.setattr(LLMClient, "generate_json", generate_json, raising=True)
    return responses


def _make_pdf(text: str = "Jane Doe\nSWE\nEXPERIENCE\nBuilt a thing\nSKILLS\nPython, AWS") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    for i, line in enumerate(text.splitlines()):
        page.insert_text((72, 72 + i * 16), line, fontsize=12)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    event = None
    for line in raw.splitlines():
        if line.startswith("event: "):
            event = line[7:].strip()
        elif line.startswith("data: ") and event is not None:
            try:
                events.append((event, json.loads(line[6:])))
            except json.JSONDecodeError:
                events.append((event, {"_raw": line[6:]}))
            event = None
    return events


def test_score_happy_path_with_mocked_llm(tmp_upload_dir, mock_llm):
    """Unified LLM call succeeds; SSE emits expected events in order."""
    mock_llm.append(UNIFIED_PAYLOAD)

    from api.main import app
    with TestClient(app) as client:
        upload = client.post(
            "/api/upload",
            files={"file": ("r.pdf", _make_pdf(), "application/pdf")},
        )
        assert upload.status_code == 200
        file_id = upload.json()["file_id"]

        r = client.post(
            "/api/score",
            json={"file_id": file_id, "jd_text": "Looking for a senior engineer with Python/AWS."},
        )
        assert r.status_code == 200, r.text
        events = _parse_sse(r.text)

        event_names = [e for e, _ in events]
        assert "init" not in event_names  # init is a progress step, not event
        assert event_names.count("progress") >= 4  # init, parsing, parsing_done, analyzing, analyzing_done, validating
        assert event_names[-1] == "complete"

        final = events[-1][1]
        assert final["report"]["overall_score"] == 78.5
        assert final["structured_resume"]["contactInfo"]["name"] == "Jane Doe"


def test_score_falls_back_to_two_calls_on_malformed_unified(tmp_upload_dir, mock_llm):
    """If unified response is malformed, the 2-call fallback should succeed."""
    # Call 1: unified — broken payload missing required fields
    mock_llm.append({"junk": True})
    # Call 2: structurer fallback — returns a valid resume
    mock_llm.append(UNIFIED_PAYLOAD["structured_resume"])
    # Call 3: scorer fallback — returns a valid ATS report
    mock_llm.append(UNIFIED_PAYLOAD["ats_report"])

    from api.main import app
    with TestClient(app) as client:
        upload = client.post(
            "/api/upload",
            files={"file": ("r.pdf", _make_pdf(), "application/pdf")},
        )
        file_id = upload.json()["file_id"]

        r = client.post(
            "/api/score",
            json={"file_id": file_id, "jd_text": "Senior engineer role."},
        )
        assert r.status_code == 200
        events = _parse_sse(r.text)

        # The 'adapting' progress step only appears on the fallback path
        progress_steps = [
            data.get("step") for ev, data in events if ev == "progress"
        ]
        assert "adapting" in progress_steps, f"got {progress_steps}"
        assert events[-1][0] == "complete"


def test_rescore_happy_path_with_mocked_llm(mock_llm):
    mock_llm.append(RESCORE_PAYLOAD)

    from api.main import app
    with TestClient(app) as client:
        body = {
            "structured_resume": UNIFIED_PAYLOAD["structured_resume"],
            "keyword_changes": [{
                "original": "Built a thing",
                "recommended": "Architected a distributed system",
            }],
            "jd_text": "Senior engineer with distributed systems experience.",
        }
        r = client.post("/api/rescore", json=body)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["report"]["overall_score"] == 88.0
        assert data["learning_suggestions"] == []  # score >= 60 → no suggestions fetched


def test_rescore_invalid_response_returns_422(mock_llm):
    mock_llm.append({"garbage": True})

    from api.main import app
    with TestClient(app) as client:
        r = client.post("/api/rescore", json={
            "structured_resume": {},
            "keyword_changes": [],
            "jd_text": "anything",
        })
        assert r.status_code == 422
        assert "malformed report" in r.json()["detail"].lower()


def test_score_unknown_provider_yields_error_event(tmp_upload_dir):
    from api.main import app
    with TestClient(app) as client:
        upload = client.post(
            "/api/upload",
            files={"file": ("r.pdf", _make_pdf(), "application/pdf")},
        )
        file_id = upload.json()["file_id"]

        r = client.post(
            "/api/score",
            json={"file_id": file_id, "jd_text": "test", "provider": "bogus"},
        )
        assert r.status_code == 200  # SSE stream returns 200, error is in-stream
        events = _parse_sse(r.text)
        assert events[0][0] == "error"
        assert "Unknown provider" in events[0][1]["message"]
