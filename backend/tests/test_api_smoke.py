"""End-to-end smoke tests for the FastAPI app (no external LLM calls).

Covers:
    * /api/health  — always available
    * /api/upload  — PDF/DOCX acceptance, bad-extension rejection
    * X-Request-ID header is echoed back on every response
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_ok():
    from api.main import app
    with TestClient(app) as client:
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
        assert r.headers.get("x-request-id")


def test_health_echoes_inbound_request_id():
    from api.main import app
    with TestClient(app) as client:
        r = client.get("/api/health", headers={"X-Request-ID": "trace-abc"})
        assert r.headers["x-request-id"] == "trace-abc"


def test_upload_rejects_unsupported_extension(tmp_upload_dir):
    from api.main import app
    with TestClient(app) as client:
        r = client.post(
            "/api/upload",
            files={"file": ("resume.txt", b"hello", "text/plain")},
        )
        assert r.status_code == 400
        assert "Unsupported format" in r.json()["detail"]


def test_upload_accepts_pdf(tmp_upload_dir, make_pdf_bytes):
    from api.main import app
    with TestClient(app) as client:
        pdf = make_pdf_bytes("Test resume content")
        r = client.post(
            "/api/upload",
            files={"file": ("resume.pdf", pdf, "application/pdf")},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["file_type"] == "pdf"
        assert body["page_count"] >= 1
        assert len(body["file_id"]) == 32  # uuid4 hex


def test_providers_endpoint(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from api.main import app
    with TestClient(app) as client:
        r = client.get("/api/providers")
        assert r.status_code == 200
        body = r.json()
        ids = {p["id"] for p in body["providers"]} if "providers" in body else {p["id"] for p in body}
        assert "local" in ids
        assert "anthropic" in ids
