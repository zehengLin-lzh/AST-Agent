"""CLI entry point for the resume parser and ATS scorer.

Usage:
    # Structured output (requires Ollama running locally)
    python main.py resume.pdf
    python main.py resume.docx -o output.json --model qwen2.5-coder:7b

    # Raw section output (no LLM needed)
    python main.py resume.pdf --raw

    # ATS scoring against a job description
    python main.py resume.pdf --score --jd job_description.txt
    python main.py resume.pdf --score --jd-text "We are looking for a …"
    python main.py resume.pdf --score --jd-url "https://boards.greenhouse.io/…"
"""

from __future__ import annotations

import argparse
import logging
import sys

log = logging.getLogger("resume_parser")


def _configure_logging() -> None:
    """Send coloured, timestamped progress lines to stderr."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="\033[90m%(asctime)s\033[0m %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Parse a PDF or DOCX resume into structured JSON, "
        "or score it against a job description.",
    )
    ap.add_argument("file", help="Path to the resume file (.pdf or .docx)")
    ap.add_argument(
        "-o", "--output",
        help="Write JSON to this file instead of stdout",
    )
    ap.add_argument(
        "--indent", type=int, default=2,
        help="JSON indentation (default: 2)",
    )

    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--raw", action="store_true",
        help="Output raw sections instead of LLM-structured JSON",
    )
    mode.add_argument(
        "--score", action="store_true",
        help="Score the resume against a job description (ATS mode)",
    )

    jd_group = ap.add_argument_group("ATS scoring options (used with --score)")
    jd_source = jd_group.add_mutually_exclusive_group()
    jd_source.add_argument(
        "--jd",
        metavar="FILE",
        help="Path to a job description text file",
    )
    jd_source.add_argument(
        "--jd-url",
        metavar="URL",
        help="URL to a job posting page (fetches and extracts text)",
    )
    jd_source.add_argument(
        "--jd-text",
        metavar="TEXT",
        help="Job description as inline text",
    )

    ap.add_argument(
        "--provider", default=None,
        help="LLM provider: local, openai, anthropic, gemini, grok (default: local, env: LLM_PROVIDER)",
    )
    ap.add_argument(
        "--model", default=None,
        help="Model name (default depends on provider, env: LLM_MODEL)",
    )
    args = ap.parse_args()
    _configure_logging()

    if args.score and not args.jd and not args.jd_url and not args.jd_text:
        ap.error("--score requires --jd <file>, --jd-url <url>, or --jd-text '<text>'")

    try:
        if args.raw:
            _run_raw(args)
        elif args.score:
            _run_score(args)
        else:
            _run_structured(args)
    except (FileNotFoundError, ValueError) as exc:
        log.error("Error: %s", exc)
        sys.exit(1)
    except ConnectionError as exc:
        log.error("Connection error: %s", exc)
        sys.exit(1)
    except RuntimeError as exc:
        log.error("Runtime error: %s", exc)
        sys.exit(1)


def _run_raw(args: argparse.Namespace) -> None:
    from src.parsers import ResumeParser

    log.info("Parsing %s (raw mode)…", args.file)
    parser = ResumeParser(args.file)
    json_str = parser.to_json(indent=args.indent)
    _output(json_str, args.output)


def _make_llm(args: argparse.Namespace):
    from src.llm import LLMClient

    kwargs: dict = {}
    if args.provider:
        kwargs["provider"] = args.provider
    if args.model:
        kwargs["model"] = args.model

    llm = LLMClient(**kwargs)
    log.info("Using %s model: %s", llm.provider_name, llm.model)
    return llm


def _run_structured(args: argparse.Namespace) -> None:
    from src.structurer import ResumeStructurer

    llm = _make_llm(args)
    structurer = ResumeStructurer(llm=llm)
    json_str = structurer.structure_to_json(args.file, indent=args.indent)
    _output(json_str, args.output)


def _run_score(args: argparse.Namespace) -> None:
    from src.scorer import ATSScorer

    llm = _make_llm(args)
    scorer = ATSScorer(llm=llm)
    json_str = scorer.score_to_json(
        args.file,
        jd_text=args.jd_text,
        jd_path=args.jd,
        jd_url=args.jd_url,
        indent=args.indent,
    )
    _output(json_str, args.output)


def _output(json_str: str, output_path: str | None) -> None:
    if output_path:
        from pathlib import Path
        Path(output_path).write_text(json_str, encoding="utf-8")
        print(f"Saved → {output_path}")
    else:
        print(json_str)


if __name__ == "__main__":
    main()
