"""Loading journal/venue rubrics and computing rubric-based decisions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .config import DEFAULT_RUBRICS_DIR
from .schemas import Recommendation, Review


@dataclass
class Criterion:
    key: str
    name: str
    description: str = ""
    weight: float = 1.0


@dataclass
class Rubric:
    id: str
    name: str
    description: str
    criteria: List[Criterion]
    scale_min: int
    scale_max: int
    thresholds: Dict[str, float]
    field_tags: List[str]

    def criteria_keys(self) -> List[str]:
        return [c.key for c in self.criteria]

    def weighted_score(self, review: Review) -> float:
        """Weighted average of a review's criterion scores for this rubric."""
        total_w = 0.0
        acc = 0.0
        for crit in self.criteria:
            s = review.score_for(crit.key)
            if s is None:
                continue
            acc += s * crit.weight
            total_w += crit.weight
        if total_w == 0:
            return 0.0
        return round(acc / total_w, 3)

    def recommend(self, weighted: float) -> Recommendation:
        t = self.thresholds
        if weighted >= t.get("accept", 4.0):
            return Recommendation.ACCEPT
        if weighted >= t.get("minor_revision", 3.25):
            return Recommendation.MINOR_REVISION
        if weighted >= t.get("major_revision", 2.5):
            return Recommendation.MAJOR_REVISION
        return Recommendation.REJECT


def load_rubric(rubric_id: str, rubrics_dir: Optional[Path] = None) -> Rubric:
    rubrics_dir = rubrics_dir or DEFAULT_RUBRICS_DIR
    path = Path(rubrics_dir) / f"{rubric_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Rubric '{rubric_id}' not found at {path}")
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    scale = data.get("scale") or {}
    criteria = [
        Criterion(
            key=c["key"],
            name=c.get("name", c["key"]),
            description=c.get("description", ""),
            weight=float(c.get("weight", 1.0)),
        )
        for c in (data.get("criteria") or [])
    ]
    return Rubric(
        id=data.get("id", rubric_id),
        name=data.get("name", rubric_id),
        description=data.get("description", ""),
        criteria=criteria,
        scale_min=int(scale.get("min", 1)),
        scale_max=int(scale.get("max", 5)),
        thresholds=data.get("decision_thresholds") or {},
        field_tags=[t.lower() for t in (data.get("field_tags") or [])],
    )


def list_rubrics(rubrics_dir: Optional[Path] = None) -> List[str]:
    rubrics_dir = Path(rubrics_dir or DEFAULT_RUBRICS_DIR)
    return sorted(p.stem for p in rubrics_dir.glob("*.yaml"))


def resolve_rubric(
    preferred_id: str,
    default_id: str = "default",
    rubrics_dir: Optional[Path] = None,
) -> Rubric:
    """Load the triage-preferred rubric, falling back to the default."""
    available = list_rubrics(rubrics_dir)
    chosen = preferred_id if preferred_id in available else default_id
    return load_rubric(chosen, rubrics_dir)
