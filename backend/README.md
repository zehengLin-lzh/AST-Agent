# AST Agent

A resume parsing toolkit that extracts structured sections from PDF and DOCX resumes into JSON. Built as the preprocessor foundation for a larger AI agent system.

## Features

- **PDF parsing** via PyMuPDF — handles single-column, two-column, and sidebar layouts (including LaTeX templates like moderncv, AltaCV, and Deedy)
- **DOCX parsing** via python-docx — leverages paragraph styles, bold text, font size, ALL-CAPS, and known-header patterns
- **Automatic section detection** for common resume headings (Summary, Experience, Education, Skills, Certifications, etc.)
- **JSON output** in a clean `[{"section": "...", "content": "..."}]` format

## Project Structure

```
├── main.py                        # CLI entry point
├── pyproject.toml                 # Project metadata & dependencies
└── src/
    ├── agents/                    # (Planned) Agent logic
    ├── llm/                       # (Planned) LLM integration
    └── preprocessor/
        ├── __init__.py
        └── resume_parser.py       # Core parser implementation
```

## Installation

Requires **Python 3.12+**.

```bash
uv venv && source .venv/bin/activate
uv pip install -e .
```

## Usage

### CLI

```bash
# Parse a PDF resume (prints JSON to stdout)
uv run main.py path/to/resume.pdf

# Parse a DOCX resume and save to a file
uv run main.py path/to/resume.docx -o output.json

# Custom JSON indentation
uv run main.py resume.pdf --indent 4
```

### Python API

```python
from src.preprocessor import parse_resume, parse_resume_to_json

# Get structured sections as a list of dicts
sections = parse_resume("resume.pdf")

# Parse and write directly to a JSON file
parse_resume_to_json("resume.docx", output_path="output.json")
```

## Dependencies

| Package | Purpose |
|---|---|
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF text and layout extraction |
| [python-docx](https://python-docx.readthedocs.io/) | DOCX document parsing |
