"""ResumeParser factory and convenience functions.

``ResumeParser("file.pdf")`` returns a :class:`PDFResumeParser` or
:class:`DOCXResumeParser` depending on the file extension.
"""

from __future__ import annotations

from pathlib import Path

from src.parsers.base import BaseResumeParser
from src.parsers.docx import DOCXResumeParser
from src.parsers.pdf import PDFResumeParser

_PARSERS: dict[str, type[BaseResumeParser]] = {
    ".pdf": PDFResumeParser,
    ".docx": DOCXResumeParser,
}


class ResumeParser:
    """Facade / factory — instantiate with a file path and call ``parse()``.

    Delegates to :class:`PDFResumeParser` or :class:`DOCXResumeParser`
    based on the file extension.

    .. code-block:: python

        sections = ResumeParser("resume.pdf").parse()
    """

    def __new__(cls, file_path: str | Path) -> BaseResumeParser:  # type: ignore[misc]
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        suffix = path.suffix.lower()
        parser_cls = _PARSERS.get(suffix)
        if parser_cls is None:
            supported = ", ".join(_PARSERS)
            raise ValueError(
                f"Unsupported format '{suffix}'. Accepted: {supported}"
            )
        return parser_cls(path)


# ── Convenience functions ────────────────────────────────────────────────────


def parse_resume(file_path: str | Path) -> list[dict[str, str]]:
    """One-liner: parse a resume file and return structured sections."""
    return ResumeParser(file_path).parse()


def parse_resume_to_json(
    file_path: str | Path,
    output_path: str | Path | None = None,
    indent: int = 2,
) -> str:
    """Parse a resume and return the JSON string. Optionally save to *output_path*."""
    parser = ResumeParser(file_path)
    if output_path:
        parser.save_json(output_path, indent=indent)
    return parser.to_json(indent=indent)
