"""Generate an optimized resume PDF by applying keyword changes.

For PDF sources: uses PyMuPDF to find and replace text spans directly in the
original PDF, fully preserving layout, fonts, and formatting.

For DOCX sources: applies keyword changes within the DOCX structure using
python-docx, then converts the result to PDF via PyMuPDF's Story API.
"""

from __future__ import annotations

import re
from pathlib import Path

import fitz  # PyMuPDF

from api.config import UPLOAD_DIR


def generate_optimized_resume(
    source_path: str,
    keyword_changes: list[dict],
) -> str:
    """Apply keyword_changes to the source resume and return path to new PDF."""
    path = Path(source_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _optimize_pdf(path, keyword_changes)
    elif suffix == ".docx":
        return _optimize_docx_to_pdf(path, keyword_changes)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def _optimize_pdf(source: Path, changes: list[dict]) -> str:
    """Edit text directly in the PDF, preserving all original formatting."""
    doc = fitz.open(str(source))

    for change in changes:
        original = change.get("original", "")
        recommended = change.get("recommended", "")
        if not original or not recommended or original == recommended:
            continue

        for page in doc:
            hits = page.search_for(original)
            if not hits:
                continue

            for rect in hits:
                page.add_redact_annot(rect, text=recommended, fontsize=0)

            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

    output_path = str(UPLOAD_DIR / f"{source.stem}_optimized.pdf")
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return output_path


def _optimize_docx_to_pdf(source: Path, changes: list[dict]) -> str:
    """Apply changes to DOCX, then convert to PDF via PyMuPDF."""
    from docx import Document as DocxDocument

    docx_doc = DocxDocument(str(source))

    for para in docx_doc.paragraphs:
        for run in para.runs:
            if run.text.strip():
                run.text = _apply_keyword_changes(run.text, changes)

    for table in docx_doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        if run.text.strip():
                            run.text = _apply_keyword_changes(run.text, changes)

    temp_docx = str(UPLOAD_DIR / f"{source.stem}_temp.docx")
    docx_doc.save(temp_docx)

    pdf_path = str(UPLOAD_DIR / f"{source.stem}_optimized.pdf")
    _docx_to_pdf(temp_docx, pdf_path)

    Path(temp_docx).unlink(missing_ok=True)
    return pdf_path


def _docx_to_pdf(docx_path: str, pdf_path: str) -> None:
    """Convert a DOCX to PDF by extracting all text and re-laying it out."""
    from docx import Document as DocxDocument
    from docx.shared import Pt

    docx_doc = DocxDocument(docx_path)
    pdf_doc = fitz.open()

    page_width = 595  # A4
    page_height = 842
    margin = 54  # ~0.75 inch
    usable_width = page_width - 2 * margin

    page = pdf_doc.new_page(width=page_width, height=page_height)
    y = margin

    for para in docx_doc.paragraphs:
        text = para.text.strip()
        if not text:
            y += 6
            continue

        style_name = (para.style.name or "").lower()
        runs = [r for r in para.runs if r.text.strip()]
        all_bold = bool(runs) and all(r.bold for r in runs)
        has_large_font = any(
            r.font.size and r.font.size.pt >= 13 for r in runs if r.font.size
        )
        is_heading = "heading" in style_name or "title" in style_name

        if is_heading or (all_bold and has_large_font):
            fontsize = 14
            fontname = "helv"
        elif all_bold:
            fontsize = 11
            fontname = "helv"
        else:
            fontsize = 10
            fontname = "helv"

        line_height = fontsize * 1.4

        if y + line_height > page_height - margin:
            page = pdf_doc.new_page(width=page_width, height=page_height)
            y = margin

        rect = fitz.Rect(margin, y, margin + usable_width, y + line_height * 3)
        rc = page.insert_textbox(
            rect, text,
            fontsize=fontsize,
            fontname=fontname,
            align=fitz.TEXT_ALIGN_LEFT,
        )

        lines_used = max(1, int(-rc / line_height) + 1) if rc < 0 else max(1, int((rect.y1 - rect.y0) / line_height))
        if rc >= 0:
            lines_used = 1
        else:
            text_len = len(text)
            chars_per_line = max(1, int(usable_width / (fontsize * 0.5)))
            lines_used = max(1, (text_len + chars_per_line - 1) // chars_per_line)

        y += line_height * lines_used + 2

    pdf_doc.save(pdf_path, garbage=4, deflate=True)
    pdf_doc.close()


def _apply_keyword_changes(text: str, changes: list[dict]) -> str:
    """Apply all keyword substitutions to a text string."""
    result = text
    for change in changes:
        original = change.get("original", "")
        recommended = change.get("recommended", "")
        if original and recommended and original != recommended:
            result = re.sub(re.escape(original), recommended, result, flags=re.IGNORECASE)
    return result
