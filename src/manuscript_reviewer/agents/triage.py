"""The triage / handling-editor agent.

Reads the paper's front matter, determines its field and type, selects the
review rubric, and defines the two independent reviewer personas. This is the
"understand scope first, then assign roles" step.
"""

from __future__ import annotations

from typing import List

from ..llm.base import LLMClient, extract_json
from ..rubrics import Rubric, list_rubrics, load_rubric
from ..schemas import ManuscriptSections, TriageResult
from .prompts import load_prompt


class TriageAgent:
    SYSTEM = (
        "You are a meticulous scholarly handling editor who routes submissions "
        "to the right reviewers. You always answer with strict JSON."
    )

    def __init__(self, client: LLMClient, rubrics_dir=None) -> None:
        self.client = client
        self.rubrics_dir = rubrics_dir

    def _rubric_catalog(self) -> str:
        lines = []
        for rid in list_rubrics(self.rubrics_dir):
            r = load_rubric(rid, self.rubrics_dir)
            tags = ", ".join(r.field_tags) if r.field_tags else "general"
            lines.append(f"- {r.id}: {r.name} (fields: {tags})")
        return "\n".join(lines)

    def run(self, manuscript: ManuscriptSections) -> TriageResult:
        prompt = load_prompt("triage").format(
            rubric_catalog=self._rubric_catalog(),
            manuscript_brief=manuscript.brief(),
        )
        raw = self.client.complete(self.SYSTEM, prompt, json_mode=True)
        data = extract_json(raw)

        personas: List[str] = data.get("reviewer_personas") or []
        if len(personas) < 2:
            personas = (personas + [
                "a senior domain expert",
                "a methodology and reproducibility specialist",
            ])[:2]

        return TriageResult(
            field=data.get("field", "unknown"),
            subfield=data.get("subfield", ""),
            paper_type=data.get("paper_type", ""),
            summary=data.get("summary", ""),
            recommended_rubric=data.get("recommended_rubric", "default"),
            reviewer_personas=personas,
            confidence=float(data.get("confidence", 0.5)),
        )
