"""Structured data models shared across the review pipeline.

Keeping agent inputs and outputs as typed schemas (rather than free-form text)
is what makes the independent reviews comparable and the final decision
rule-based rather than vibe-based.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Recommendation(str, Enum):
    """The four standard peer-review outcomes."""

    ACCEPT = "accept"
    MINOR_REVISION = "minor_revision"
    MAJOR_REVISION = "major_revision"
    REJECT = "reject"


class ManuscriptSections(BaseModel):
    """A parsed manuscript, split into the parts agents reason over."""

    title: str = ""
    abstract: str = ""
    body: str = ""
    references: str = ""
    # The full text actually sent to models (post-redaction).
    full_text: str = ""
    # Metadata removed during redaction, kept locally for the final report only.
    redacted_identity: List[str] = Field(default_factory=list)

    def brief(self, max_chars: int = 6000) -> str:
        """A compact representation for the triage step."""
        parts = [p for p in (self.title, self.abstract) if p]
        text = "\n\n".join(parts)
        if len(text) < max_chars:
            # Pad with the opening of the body for extra signal.
            text = (text + "\n\n" + self.body)[:max_chars]
        return text[:max_chars]


class TriageResult(BaseModel):
    """Output of the editor/triage agent: what is this paper and who should review it."""

    field: str
    subfield: str = ""
    paper_type: str = ""
    summary: str = ""
    recommended_rubric: str = Field(
        ..., description="id of the rubric best matching this paper"
    )
    reviewer_personas: List[str] = Field(
        default_factory=list,
        description="Distinct expert personas for the independent reviewers",
    )
    confidence: float = Field(0.5, ge=0.0, le=1.0)


class CriterionScore(BaseModel):
    """A single reviewer's score and reasoning for one rubric dimension."""

    key: str
    score: float
    justification: str = ""


class Review(BaseModel):
    """One independent reviewer's complete assessment."""

    reviewer_id: str
    persona: str = ""
    summary: str = ""
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    criterion_scores: List[CriterionScore] = Field(default_factory=list)
    recommendation: Recommendation
    path_to_acceptance: List[str] = Field(
        default_factory=list,
        description="Concrete, actionable steps the authors can take to be accepted",
    )
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    weighted_score: Optional[float] = None

    def score_for(self, key: str) -> Optional[float]:
        for cs in self.criterion_scores:
            if cs.key == key:
                return cs.score
        return None


class FinalDecision(BaseModel):
    """The meta-reviewer's reconciliation of the independent reviews."""

    accepted: bool
    recommendation: Recommendation
    rationale: str = ""
    consensus_points: List[str] = Field(default_factory=list)
    disagreements: List[str] = Field(default_factory=list)
    required_changes: List[str] = Field(default_factory=list)
    author_letter: str = ""
    mean_weighted_score: Optional[float] = None
