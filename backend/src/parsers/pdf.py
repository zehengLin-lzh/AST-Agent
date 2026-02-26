"""PDF resume parser using PyMuPDF.

Handles single-column, symmetric two-column, and sidebar layouts
commonly produced by LaTeX templates (moderncv, AltaCV, Deedy, …).
"""

from __future__ import annotations

import fitz

from src.constants import (
    BOLD_FLAG,
    COL_MIN_RATIO,
    FONT_HEADER_RATIO,
    FULL_WIDTH_RATIO,
    MAX_HEADER_CHARS,
    MAX_HEADER_WORDS,
)
from src.models.text_line import TextLine
from src.parsers.base import BaseResumeParser


class PDFResumeParser(BaseResumeParser):
    """Parse a **PDF** resume into ``[{section, content}, …]``."""

    def parse(self) -> list[dict[str, str]]:
        doc = fitz.open(str(self.file_path))
        all_lines: list[TextLine] = []
        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                lines = self._extract_lines(page, page_idx)
                lines = self._reorder_columns(lines, page.rect.width)
                all_lines.extend(lines)
        finally:
            doc.close()

        if not all_lines:
            return [{
                "section": "Error",
                "content": (
                    "No extractable text found. "
                    "The PDF may be scanned / image-based and requires OCR."
                ),
            }]

        return self._build_sections(all_lines)

    # ── line extraction ──────────────────────────────────────────

    @staticmethod
    def _extract_lines(page: fitz.Page, page_num: int) -> list[TextLine]:
        """Extract every visual text line from *page* with style metadata."""
        lines: list[TextLine] = []
        data = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

        for block in data.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line_dict in block.get("lines", []):
                spans = line_dict.get("spans", [])
                if not spans:
                    continue

                parts: list[str] = []
                max_size = 0.0
                dominant_font = ""
                bold_chars = 0
                total_chars = 0

                for span in spans:
                    t = span.get("text", "")
                    parts.append(t)
                    size = span.get("size", 0.0)
                    if size > max_size:
                        max_size = size
                        dominant_font = span.get("font", "")
                    n = len(t.strip())
                    total_chars += n
                    font_lower = span.get("font", "").lower()
                    if (
                        (span.get("flags", 0) & BOLD_FLAG)
                        or "bold" in font_lower
                        or "black" in font_lower
                    ):
                        bold_chars += n

                full_text = "".join(parts).strip()
                if not full_text:
                    continue

                bbox = line_dict.get("bbox", (0, 0, 0, 0))
                lines.append(TextLine(
                    text=full_text,
                    x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3],
                    font_size=max_size,
                    font_name=dominant_font,
                    is_bold=(total_chars > 0 and bold_chars / total_chars > 0.5),
                    page_num=page_num,
                ))
        return lines

    # ── two-column reorder ───────────────────────────────────────

    @staticmethod
    def _reorder_columns(
        lines: list[TextLine], page_width: float
    ) -> list[TextLine]:
        """Detect a multi-column layout and reorder for natural reading.

        Distinguishes two layout families:

        * **Independent columns** (sidebar / newspaper) — each side has its own
          section headers.  Read left top-to-bottom, then right top-to-bottom.
        * **Label-content** (common LaTeX templates) — section headers live on
          one side only; the other side holds dates, bullets, etc. at matching
          Y-positions.  Merge both sides sorted by Y then X.
        """
        if len(lines) < 4:
            return sorted(lines, key=lambda l: (l.y0, l.x0))

        mid = page_width / 2
        left: list[TextLine] = []
        right: list[TextLine] = []
        full_width: list[TextLine] = []

        for ln in lines:
            if ln.width > page_width * FULL_WIDTH_RATIO:
                full_width.append(ln)
            elif ln.center_x < mid:
                left.append(ln)
            else:
                right.append(ln)

        total = len(left) + len(right) + len(full_width)
        if total == 0:
            return lines

        if (
            len(left) / total < COL_MIN_RATIO
            or len(right) / total < COL_MIN_RATIO
        ):
            return sorted(lines, key=lambda l: (l.y0, l.x0))

        left_headers = sum(
            1 for l in left
            if BaseResumeParser.matches_known_header(l.text.strip())
        )
        right_headers = sum(
            1 for l in right
            if BaseResumeParser.matches_known_header(l.text.strip())
        )

        if left_headers >= 2 and right_headers >= 2:
            left.sort(key=lambda l: l.y0)
            right.sort(key=lambda l: l.y0)
            full_width.sort(key=lambda l: l.y0)

            col_top = min(
                (l.y0 for l in left + right), default=float("inf")
            )
            top_fw = [l for l in full_width if l.y0 <= col_top + 5]
            bottom_fw = [l for l in full_width if l.y0 > col_top + 5]
            return top_fw + left + right + bottom_fw

        return sorted(lines, key=lambda l: (l.y0, l.x0))

    # ── header detection ─────────────────────────────────────────

    @staticmethod
    def _is_section_header(line: TextLine, median_size: float) -> bool:
        text = line.text.strip()
        if not text or len(text) > MAX_HEADER_CHARS:
            return False
        if len(text.split()) > MAX_HEADER_WORDS:
            return False

        known = BaseResumeParser.matches_known_header(text)
        larger = line.font_size >= median_size * FONT_HEADER_RATIO
        bold = line.is_bold
        upper = (
            text == text.upper()
            and len(text) > 2
            and any(c.isalpha() for c in text)
        )

        if known and (larger or bold or upper):
            return True
        if larger and bold:
            return True
        if upper and bold and len(text.split()) <= 4:
            return True
        if known and upper:
            return True
        return False

    # ── section builder ──────────────────────────────────────────

    def _build_sections(self, lines: list[TextLine]) -> list[dict[str, str]]:
        if not lines:
            return []

        sizes = sorted(l.font_size for l in lines)
        median_size = sizes[len(sizes) // 2]

        entries: list[tuple[str, bool]] = [
            (line.text, self._is_section_header(line, median_size))
            for line in lines
        ]
        return self._collect_sections(entries)
