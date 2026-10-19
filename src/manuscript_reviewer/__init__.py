"""A privacy-aware multi-agent system for scholarly manuscript peer review."""

from .schemas import (
    CriterionScore,
    FinalDecision,
    ManuscriptSections,
    Recommendation,
    Review,
    TriageResult,
)

__all__ = [
    "CriterionScore",
    "FinalDecision",
    "ManuscriptSections",
    "Recommendation",
    "Review",
    "TriageResult",
]

__version__ = "0.1.0"
