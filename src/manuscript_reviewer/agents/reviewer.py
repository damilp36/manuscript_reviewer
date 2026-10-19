"""An independent reviewer agent.

Each reviewer scores the manuscript against the rubric and recommends an
outcome, plus a concrete path to acceptance. Reviewers run independently and
never see one another's output.
"""

from __future__ import annotations

from ..llm.base import LLMClient, extract_json
from ..rubrics import Rubric
from ..schemas import CriterionScore, ManuscriptSections, Recommendation, Review
from .prompts import load_prompt


class ReviewerAgent:
    def __init__(self, client: LLMClient, reviewer_id: str, persona: str) -> None:
        self.client = client
        self.reviewer_id = reviewer_id
        self.persona = persona

    def _criteria_block(self, rubric: Rubric) -> str:
        return "\n".join(
            f"- {c.key} ({c.name}, weight {c.weight}): {c.description}"
            for c in rubric.criteria
        )

    def run(self, manuscript: ManuscriptSections, rubric: Rubric) -> Review:
        system = (
            f"You are {self.persona}, an impartial expert peer reviewer. "
            "You always answer with strict JSON."
        )
        prompt = load_prompt("reviewer").format(
            persona=self.persona,
            venue_name=rubric.name,
            scale_min=rubric.scale_min,
            scale_max=rubric.scale_max,
            criteria_block=self._criteria_block(rubric),
            criterion_keys=", ".join(rubric.criteria_keys()),
            manuscript_text=manuscript.full_text,
        )
        raw = self.client.complete(system, prompt, json_mode=True)
        data = extract_json(raw)

        scores = [
            CriterionScore(
                key=cs.get("key", ""),
                score=_clamp(cs.get("score", 0), rubric.scale_min, rubric.scale_max),
                justification=cs.get("justification", ""),
            )
            for cs in data.get("criterion_scores", [])
            if cs.get("key")
        ]

        review = Review(
            reviewer_id=self.reviewer_id,
            persona=self.persona,
            summary=data.get("summary", ""),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            criterion_scores=scores,
            recommendation=_coerce_rec(data.get("recommendation")),
            path_to_acceptance=data.get("path_to_acceptance", []),
            confidence=float(data.get("confidence", 0.5)),
        )
        # Compute the rubric-weighted score so the judge has a consistent number.
        review.weighted_score = rubric.weighted_score(review)
        return review


def _clamp(value, lo: int, hi: int) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return float(lo)
    return float(max(lo, min(hi, v)))


def _coerce_rec(value) -> Recommendation:
    if isinstance(value, Recommendation):
        return value
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    try:
        return Recommendation(text)
    except ValueError:
        return Recommendation.MAJOR_REVISION
