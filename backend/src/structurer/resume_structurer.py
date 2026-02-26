"""Two-stage pipeline: raw parse then LLM structuring.

Pipeline:
    PDF / DOCX  -->  ResumeParser (raw sections)  -->  LLM  -->  StructuredResume
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from src.llm.client import LLMClient
from src.models.resume import StructuredResume
from src.parsers.factory import ResumeParser
from src.structurer.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

log = logging.getLogger(__name__)


class ResumeStructurer:
    """Two-stage pipeline: raw parse then LLM structuring.

    Usage::

        structurer = ResumeStructurer()                   # default Ollama model
        result = structurer.structure("resume.pdf")       # StructuredResume
        print(result.model_dump_json(indent=2))
    """

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    def structure(self, file_path: str | Path) -> StructuredResume:
        """Parse *file_path* and return a validated :class:`StructuredResume`."""
        log.info("Stage 1/3 — Extracting text from %s…", Path(file_path).name)
        t0 = time.perf_counter()
        raw_sections = ResumeParser(file_path).parse()
        log.info(
            "  Extracted %d sections in %.1fs",
            len(raw_sections),
            time.perf_counter() - t0,
        )

        resume_text = self._sections_to_text(raw_sections)
        log.info(
            "Stage 2/3 — Sending to LLM (%s) for structured extraction…",
            self.llm.model,
        )
        t1 = time.perf_counter()
        data = self.llm.generate_json(
            prompt=USER_PROMPT_TEMPLATE.format(resume_text=resume_text),
            system=SYSTEM_PROMPT,
        )
        log.info("  LLM responded in %.1fs", time.perf_counter() - t1)

        log.info("Stage 3/3 — Validating against schema…")
        result = StructuredResume.model_validate(data)
        log.info(
            "  Done — %d experience entries, %d skills, %d education entries",
            len(result.experience),
            len(result.skill),
            len(result.education),
        )
        return result

    def structure_to_dict(self, file_path: str | Path) -> dict:
        """Same as :meth:`structure` but returns a plain dict."""
        return self.structure(file_path).model_dump()

    def structure_to_json(
        self,
        file_path: str | Path,
        output_path: str | Path | None = None,
        indent: int = 2,
    ) -> str:
        """Parse, structure, and return a JSON string.
        Optionally write to *output_path*.
        """
        result = self.structure(file_path)
        json_str = result.model_dump_json(indent=indent)
        if output_path:
            Path(output_path).write_text(json_str, encoding="utf-8")
        return json_str

    # ── internal ─────────────────────────────────────────────────

    @staticmethod
    def _sections_to_text(sections: list[dict[str, str]]) -> str:
        parts: list[str] = []
        for sec in sections:
            header = sec.get("section", "")
            content = sec.get("content", "")
            if header:
                parts.append(f"[{header}]")
            if content:
                parts.append(content)
            parts.append("")
        return "\n".join(parts).strip()
