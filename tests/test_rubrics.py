import pytest

from manuscript_reviewer.rubrics import list_rubrics, load_rubric, resolve_rubric
from manuscript_reviewer.schemas import CriterionScore, Recommendation, Review


def test_list_and_load_rubrics():
    ids = list_rubrics()
    assert "default" in ids
    assert "ml_conference" in ids
    r = load_rubric("ml_conference")
    assert r.criteria
    assert "soundness" in r.criteria_keys()


def test_resolve_falls_back_to_default():
    r = resolve_rubric("nonexistent_rubric", default_id="default")
    assert r.id == "default"


def test_weighted_score_and_recommendation():
    r = load_rubric("default")
    review = Review(
        reviewer_id="R1",
        recommendation=Recommendation.ACCEPT,
        criterion_scores=[
            CriterionScore(key=c.key, score=5.0) for c in r.criteria
        ],
    )
    assert r.weighted_score(review) == 5.0
    assert r.recommend(5.0) == Recommendation.ACCEPT
    assert r.recommend(2.0) == Recommendation.REJECT
    assert r.recommend(3.3) == Recommendation.MINOR_REVISION
