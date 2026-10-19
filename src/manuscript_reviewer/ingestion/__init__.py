"""Manuscript ingestion (parsing) and redaction (de-identification)."""

from .parser import parse_manuscript, read_text
from .redaction import redact_identity

__all__ = ["parse_manuscript", "read_text", "redact_identity"]
