"""Turn a manuscript file into structured sections.

Parsing is deliberately deterministic (no LLM): clean, consistent input for
every downstream agent. Supports PDF (via pypdf), plain text, and Markdown.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..schemas import ManuscriptSections

_ABSTRACT_RE = re.compile(r"(?im)^\s*abstract\s*[:\.\-]?\s*$")
_REFERENCES_RE = re.compile(r"(?im)^\s*(references|bibliography)\s*[:\.\-]?\s*$")
# Headings that typically mark the end of the abstract / start of the body.
_BODY_START_RE = re.compile(
    r"(?im)^\s*(1\.?\s+)?(introduction|background|1\s+introduction)\s*$"
)


def read_text(path: str | Path) -> str:
    """Read raw text from a PDF, txt, or md file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() == ".pdf":
        return _read_pdf(path)
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - optional dep
        raise ImportError(
            "Reading PDF manuscripts requires 'pypdf'. Install with: pip install pypdf"
        ) from exc

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def parse_manuscript(source: str | Path, *, is_text: bool = False) -> ManuscriptSections:
    """Parse a file path (default) or a raw text string (is_text=True)."""
    text = str(source) if is_text else read_text(source)
    text = _normalize(text)

    title = _guess_title(text)
    abstract = _extract_abstract(text)
    references = _extract_references(text)
    body = _extract_body(text, abstract, references)

    return ManuscriptSections(
        title=title,
        abstract=abstract,
        body=body,
        references=references,
        full_text=text,
    )


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _guess_title(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if len(line) > 8 and not line.lower().startswith("abstract"):
            return line[:300]
    return ""


def _extract_abstract(text: str) -> str:
    m = _ABSTRACT_RE.search(text)
    if not m:
        # Fall back: text between title block and first section heading.
        body_m = _BODY_START_RE.search(text)
        if body_m:
            return text[: body_m.start()].strip()[-2000:]
        return ""
    start = m.end()
    end_m = _BODY_START_RE.search(text, start)
    end = end_m.start() if end_m else min(start + 3000, len(text))
    return text[start:end].strip()


def _extract_references(text: str) -> str:
    m = _REFERENCES_RE.search(text)
    if not m:
        return ""
    return text[m.end():].strip()


def _extract_body(text: str, abstract: str, references: str) -> str:
    body = text
    if abstract and abstract in body:
        body = body.split(abstract, 1)[1]
    if references and references in body:
        body = body.split(references, 1)[0]
    return body.strip()
