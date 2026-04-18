"""Tests for PDFResumeParser error-handling and fallback paths.

These tests exercise the specific bare-except fixes from O3:
    * missing file  → structured error section, no crash
    * corrupt bytes → structured error section with exc_type in message
    * valid PDF     → at least one non-error section returned
"""

from __future__ import annotations

from pathlib import Path

from src.parsers.pdf import PDFResumeParser


def test_missing_file_returns_error_section(tmp_path):
    missing = tmp_path / "nope.pdf"
    result = PDFResumeParser(missing).parse()
    assert result == [{
        "section": "Error",
        "content": "The PDF file was not found on disk.",
    }]


def test_corrupt_file_returns_error_section(tmp_path):
    corrupt = tmp_path / "bad.pdf"
    corrupt.write_bytes(b"this is definitely not a PDF")

    result = PDFResumeParser(corrupt).parse()

    assert len(result) == 1
    assert result[0]["section"] == "Error"
    assert "Could not open PDF" in result[0]["content"]


def test_valid_pdf_yields_content(tmp_path, make_pdf_bytes):
    pdf = tmp_path / "ok.pdf"
    pdf.write_bytes(make_pdf_bytes("John Doe\nSoftware Engineer"))

    result = PDFResumeParser(pdf).parse()

    assert result, "parser should return at least one section"
    assert all(section["section"] != "Error" for section in result)
    combined = " ".join(s.get("content", "") for s in result)
    assert "John Doe" in combined


def test_empty_pdf_triggers_ocr_error_message(tmp_path):
    """A PDF with no extractable text should return the 'requires OCR' error."""
    import fitz

    doc = fitz.open()
    doc.new_page()  # blank page
    path = tmp_path / "blank.pdf"
    doc.save(str(path))
    doc.close()

    result = PDFResumeParser(path).parse()

    assert len(result) == 1
    assert result[0]["section"] == "Error"
    assert "OCR" in result[0]["content"] or "No extractable text" in result[0]["content"]
