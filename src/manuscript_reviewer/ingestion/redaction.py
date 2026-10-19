"""De-identify a manuscript before it is sent to any model.

This supports double-blind review and reduces PII exposure. It removes author
names/affiliations (the block between the title and the abstract),
acknowledgements, funding statements, and email addresses.

Important: redaction protects *author identity*. It does NOT protect the
manuscript's ideas/IP. For sensitive IP, use a local provider (ollama/mock).
"""

from __future__ import annotations

import re

from ..schemas import ManuscriptSections

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_ACK_RE = re.compile(
    r"(?is)\n\s*(acknowledgements?|acknowledgments?|funding)\b.*?"
    r"(?=\n\s*(references|bibliography|appendix)\b|\Z)"
)


def redact_identity(sections: ManuscriptSections) -> ManuscriptSections:
    removed: list[str] = []

    # 1. Author/affiliation block: text between the title line and the abstract.
    author_block = ""
    if sections.title and sections.abstract:
        full = sections.full_text
        t_idx = full.find(sections.title)
        a_idx = full.find(sections.abstract)
        if t_idx != -1 and a_idx != -1 and a_idx > t_idx:
            author_block = full[t_idx + len(sections.title) : a_idx].strip()

    def scrub(text: str) -> str:
        nonlocal removed
        if author_block and author_block in text:
            removed.append(author_block)
            text = text.replace(author_block, "\n[AUTHOR IDENTITY REDACTED]\n")
        for email in set(_EMAIL_RE.findall(text)):
            removed.append(email)
        text = _EMAIL_RE.sub("[EMAIL REDACTED]", text)
        text, n = _ACK_RE.subn("\n[ACKNOWLEDGEMENTS REDACTED]\n", text)
        if n:
            removed.append("acknowledgements/funding section")
        return text

    redacted = sections.model_copy(deep=True)
    redacted.full_text = scrub(sections.full_text)
    redacted.body = scrub(sections.body)
    redacted.abstract = _EMAIL_RE.sub("[EMAIL REDACTED]", sections.abstract)
    redacted.redacted_identity = sorted(set(removed))
    return redacted
