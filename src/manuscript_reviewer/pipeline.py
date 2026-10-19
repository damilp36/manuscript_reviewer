"""End-to-end orchestration: parse -> redact -> triage -> reviews -> decision."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .agents import JudgeAgent, ReviewerAgent, TriageAgent
from .config import AppConfig, load_config
from .ingestion import parse_manuscript, redact_identity
from .llm.factory import build_client
from .rubrics import Rubric, resolve_rubric
from .schemas import FinalDecision, ManuscriptSections, Review, TriageResult


@dataclass
class ReviewReport:
    manuscript_title: str
    triage: TriageResult
    rubric_id: str
    rubric_name: str
    reviews: List[Review]
    decision: FinalDecision
    redacted_items: List[str]

    def to_dict(self) -> dict:
        return {
            "manuscript_title": self.manuscript_title,
            "triage": self.triage.model_dump(),
            "rubric": {"id": self.rubric_id, "name": self.rubric_name},
            "reviews": [r.model_dump() for r in self.reviews],
            "decision": self.decision.model_dump(),
            "redacted_items": self.redacted_items,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_markdown(self) -> str:
        return render_markdown(self)


class ReviewPipeline:
    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self.config = config or load_config()

    def _client(self, role: str):
        return build_client(self.config.role(role), self.config)

    def run(
        self,
        source: str | Path,
        *,
        is_text: bool = False,
    ) -> ReviewReport:
        # 1. Parse (deterministic).
        manuscript = parse_manuscript(source, is_text=is_text)

        # 2. Redact author identity for double-blind review.
        if self.config.redact_author_identity:
            manuscript = redact_identity(manuscript)

        # 3. Triage: understand scope, pick rubric and reviewer personas.
        triage = TriageAgent(self._client("triage"), self.config.rubrics_dir).run(
            manuscript
        )

        # 4. Resolve the rubric (fall back to default if triage's pick is unknown).
        rubric: Rubric = resolve_rubric(
            triage.recommended_rubric,
            default_id=self.config.default_rubric,
            rubrics_dir=self.config.rubrics_dir,
        )

        # 5. Independent reviews.
        reviews = self._run_reviews(manuscript, rubric, triage)

        # 6. Judge reconciles into a final decision.
        decision = JudgeAgent(self._client("judge")).run(reviews, rubric)

        return ReviewReport(
            manuscript_title=manuscript.title,
            triage=triage,
            rubric_id=rubric.id,
            rubric_name=rubric.name,
            reviews=reviews,
            decision=decision,
            redacted_items=manuscript.redacted_identity,
        )

    def _run_reviews(
        self,
        manuscript: ManuscriptSections,
        rubric: Rubric,
        triage: TriageResult,
    ) -> List[Review]:
        n = max(1, self.config.num_reviewers)
        personas = triage.reviewer_personas or ["a senior domain expert"]
        reviews: List[Review] = []
        for i in range(n):
            persona = personas[i % len(personas)]
            # A fresh client per reviewer keeps them independent.
            agent = ReviewerAgent(
                self._client("reviewer"),
                reviewer_id=f"Reviewer {i + 1}",
                persona=persona,
            )
            reviews.append(agent.run(manuscript, rubric))
        return reviews


def render_markdown(report: ReviewReport) -> str:
    d = report.decision
    lines: List[str] = []
    lines.append(f"# Peer Review Report: {report.manuscript_title or 'Untitled'}")
    lines.append("")
    lines.append(f"**Decision:** {d.recommendation.value.replace('_', ' ').title()} "
                 f"({'ACCEPTED' if d.accepted else 'NOT ACCEPTED'})")
    if d.mean_weighted_score is not None:
        lines.append(f"**Mean weighted score:** {d.mean_weighted_score}")
    lines.append("")

    lines.append("## Triage")
    t = report.triage
    lines.append(f"- **Field:** {t.field} / {t.subfield}")
    lines.append(f"- **Paper type:** {t.paper_type}")
    lines.append(f"- **Rubric applied:** {report.rubric_name} (`{report.rubric_id}`)")
    lines.append(f"- **Summary:** {t.summary}")
    lines.append("")

    for r in report.reviews:
        lines.append(f"## {r.reviewer_id} — {r.persona}")
        lines.append(f"*Recommendation:* **{r.recommendation.value}**  |  "
                     f"*Weighted score:* {r.weighted_score}  |  "
                     f"*Confidence:* {r.confidence}")
        lines.append("")
        lines.append(f"{r.summary}")
        lines.append("")
        if r.strengths:
            lines.append("**Strengths**")
            lines += [f"- {s}" for s in r.strengths]
            lines.append("")
        if r.weaknesses:
            lines.append("**Weaknesses**")
            lines += [f"- {w}" for w in r.weaknesses]
            lines.append("")
        if r.criterion_scores:
            lines.append("**Scores**")
            lines.append("")
            lines.append("| Criterion | Score | Justification |")
            lines.append("|---|---|---|")
            for cs in r.criterion_scores:
                just = cs.justification.replace("|", "\\|")
                lines.append(f"| {cs.key} | {cs.score} | {just} |")
            lines.append("")
        if r.path_to_acceptance:
            lines.append("**Path to acceptance**")
            lines += [f"- {p}" for p in r.path_to_acceptance]
            lines.append("")

    lines.append("## Final Decision (Area Chair)")
    lines.append(f"**Recommendation:** {d.recommendation.value}")
    lines.append("")
    lines.append(d.rationale)
    lines.append("")
    if d.consensus_points:
        lines.append("**Consensus**")
        lines += [f"- {c}" for c in d.consensus_points]
        lines.append("")
    if d.disagreements:
        lines.append("**Disagreements & resolution**")
        lines += [f"- {c}" for c in d.disagreements]
        lines.append("")
    if d.required_changes:
        lines.append("**Required changes for acceptance**")
        lines += [f"- {c}" for c in d.required_changes]
        lines.append("")
    if d.author_letter:
        lines.append("## Decision Letter to Authors")
        lines.append("")
        lines.append(d.author_letter)
        lines.append("")
    if report.redacted_items:
        lines.append("---")
        lines.append(f"_Redacted before review: {len(report.redacted_items)} "
                     "author-identifying item(s)._")

    return "\n".join(lines)
