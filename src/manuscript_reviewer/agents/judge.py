"""The meta-reviewer / Area Chair agent.

Reconciles the independent reviews into one decision, resolving disagreements
explicitly, and writes the author decision letter. The final accept/reject is
grounded in the rubric's weighted-score thresholds, not just model prose.
"""

from __future__ import annotations

from statistics import mean
from typing import List

from ..llm.base import LLMClient, extract_json
from ..rubrics import Rubric
from ..schemas import FinalDecision, Recommendation, Review
from .prompts import load_prompt
from .reviewer import _coerce_rec


class JudgeAgent:
    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def _reviews_block(self, reviews: List[Review]) -> str:
        blocks = []
        for r in reviews:
            lines = [
                f"### {r.reviewer_id} (persona: {r.persona})",
                f"Recommendation: {r.recommendation.value}",
                f"Weighted score: {r.weighted_score}",
                f"Summary: {r.summary}",
                "Strengths: " + "; ".join(r.strengths),
                "Weaknesses: " + "; ".join(r.weaknesses),
                "Path to acceptance: " + "; ".join(r.path_to_acceptance),
            ]
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    def _score_summary(self, reviews: List[Review]) -> str:
        return "\n".join(
            f"- {r.reviewer_id}: weighted {r.weighted_score} "
            f"(rec: {r.recommendation.value})"
            for r in reviews
        )

    def run(self, reviews: List[Review], rubric: Rubric) -> FinalDecision:
        scored = [r.weighted_score for r in reviews if r.weighted_score is not None]
        mean_score = round(mean(scored), 3) if scored else None

        prompt = load_prompt("judge").format(
            venue_name=rubric.name,
            score_summary=self._score_summary(reviews),
            reviews_block=self._reviews_block(reviews),
        )
        raw = self.client.complete(
            "You are a fair, decisive Area Chair. You always answer with strict JSON.",
            prompt,
            json_mode=True,
        )
        data = extract_json(raw)

        # The rubric thresholds provide an objective anchor for the decision.
        rubric_rec = (
            rubric.recommend(mean_score) if mean_score is not None else None
        )
        llm_rec = _coerce_rec(data.get("recommendation"))
        final_rec = llm_rec or rubric_rec or Recommendation.MAJOR_REVISION

        return FinalDecision(
            accepted=final_rec in (Recommendation.ACCEPT, Recommendation.MINOR_REVISION),
            recommendation=final_rec,
            rationale=data.get("rationale", ""),
            consensus_points=data.get("consensus_points", []),
            disagreements=data.get("disagreements", []),
            required_changes=data.get("required_changes", []),
            author_letter=data.get("author_letter", ""),
            mean_weighted_score=mean_score,
        )
