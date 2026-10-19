"""Shared pytest fixtures."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from manuscript_reviewer.config import load_config  # noqa: E402


@pytest.fixture
def sample_text() -> str:
    return (ROOT / "examples" / "sample_manuscript.txt").read_text(encoding="utf-8")


@pytest.fixture
def mock_config():
    """A config where every role uses the deterministic Mock backend."""
    cfg = load_config()
    for role in cfg.roles.values():
        role.provider = "mock"
        role.model = "mock"
    cfg.local_only = False
    return cfg
