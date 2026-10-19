"""Shared helpers for agents (prompt loading)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from ..config import PROJECT_ROOT

PROMPTS_DIR = PROJECT_ROOT / "prompts"


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """Load a prompt template by filename stem from the prompts/ directory."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")
