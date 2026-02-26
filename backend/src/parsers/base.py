"""Abstract base class for all resume parsers.

Provides shared section-building logic, JSON serialisation, and the
``matches_known_header`` helper that both PDF and DOCX parsers rely on.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from src.constants import matches_known_header


class BaseResumeParser(ABC):
    """Abstract base with shared section-building logic and JSON output."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    # ── public API ───────────────────────────────────────────────

    @abstractmethod
    def parse(self) -> list[dict[str, str]]:
        """Return ``[{"section": …, "content": …}, …]``."""

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.parse(), indent=indent, ensure_ascii=False)

    def save_json(self, output_path: str | Path, indent: int = 2) -> Path:
        out = Path(output_path)
        out.write_text(self.to_json(indent=indent), encoding="utf-8")
        return out

    # ── shared helpers ───────────────────────────────────────────

    @staticmethod
    def matches_known_header(text: str) -> bool:
        """Delegate to the canonical implementation in :mod:`src.constants`."""
        return matches_known_header(text)

    @staticmethod
    def _collect_sections(
        entries: list[tuple[str, bool]],
    ) -> list[dict[str, str]]:
        """Build ``[{section, content}, …]`` from a flat list of
        ``(text, is_header)`` pairs."""
        sections: list[dict[str, str]] = []
        header: str | None = None
        content_lines: list[str] = []

        for text, is_heading in entries:
            if is_heading:
                if header is not None or content_lines:
                    sections.append({
                        "section": header or "Personal Information",
                        "content": "\n".join(content_lines).strip(),
                    })
                header = text
                content_lines = []
            else:
                content_lines.append(text)

        if header is not None or content_lines:
            sections.append({
                "section": header or "Personal Information",
                "content": "\n".join(content_lines).strip(),
            })

        return [s for s in sections if s.get("content") or s.get("section")]
