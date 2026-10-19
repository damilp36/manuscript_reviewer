"""Deterministic offline backend for tests and dry runs.

The Mock backend performs no real reasoning. It inspects which JSON schema the
caller asked for and returns a well-formed, deterministic response so the full
pipeline can run end-to-end with no model, no network, and no data leaving the
machine.
"""

from __future__ import annotations

import json
from typing import Any

from .base import LLMClient


class MockClient(LLMClient):
    @property
    def is_local(self) -> bool:
        return True

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = False,
        temperature: float | None = None,
    ) -> str:
        prompt = f"{system}\n{user}"

        # Triage request: identified by its distinctive output keys.
        if "recommended_rubric" in prompt:
            return json.dumps(
                {
                    "field": "machine learning",
                    "subfield": "natural language processing",
                    "paper_type": "empirical study",
                    "summary": "A mock triage summary of the submitted manuscript.",
                    "recommended_rubric": "ml_conference",
                    "reviewer_personas": [
                        "an empirical ML methods expert",
                        "a statistics and reproducibility specialist",
                    ],
                    "confidence": 0.8,
                }
            )

        # Judge request.
        if "author_letter" in prompt:
            return json.dumps(
                {
                    "recommendation": "major_revision",
                    "rationale": "Mock reconciliation of two independent reviews.",
                    "consensus_points": ["The problem is relevant."],
                    "disagreements": ["Reviewers differ on novelty."],
                    "required_changes": [
                        "Add stronger baselines.",
                        "Report statistical significance.",
                    ],
                    "author_letter": "Dear authors, this is a mock decision letter.",
                }
            )

        # Otherwise treat as a reviewer request. Derive criterion keys from the
        # schema the agent injected into the prompt.
        keys = self._criterion_keys_from_prompt(prompt)
        return json.dumps(
            {
                "summary": "A mock independent review of the manuscript.",
                "strengths": ["Clear motivation.", "Readable presentation."],
                "weaknesses": ["Limited evaluation.", "Missing ablations."],
                "criterion_scores": [
                    {
                        "key": k,
                        "score": 3,
                        "justification": f"Mock justification for {k}.",
                    }
                    for k in keys
                ],
                "recommendation": "major_revision",
                "path_to_acceptance": [
                    "Strengthen the empirical evaluation.",
                    "Clarify the novelty relative to prior work.",
                ],
                "confidence": 0.6,
            }
        )

    @staticmethod
    def _criterion_keys_from_prompt(prompt: str) -> list[str]:
        """Pull the rubric criterion keys the agent listed, with a fallback."""
        keys: list[str] = []
        marker = "CRITERION_KEYS:"
        if marker in prompt:
            segment = prompt.split(marker, 1)[1].splitlines()[0]
            keys = [k.strip() for k in segment.split(",") if k.strip()]
        return keys or ["originality", "soundness", "clarity"]
