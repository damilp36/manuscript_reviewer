from manuscript_reviewer.pipeline import ReviewPipeline
from manuscript_reviewer.schemas import Recommendation


def test_full_pipeline_with_mock_backend(sample_text, mock_config, tmp_path):
    # Write the sample to a file so we exercise the file path too.
    path = tmp_path / "paper.txt"
    path.write_text(sample_text, encoding="utf-8")

    report = ReviewPipeline(mock_config).run(path)

    # Triage chose a rubric and personas.
    assert report.rubric_id in ("ml_conference", "default")
    assert len(report.triage.reviewer_personas) == 2

    # Two independent reviews were produced and scored.
    assert len(report.reviews) == mock_config.num_reviewers
    for r in report.reviews:
        assert r.criterion_scores
        assert r.weighted_score is not None
        assert isinstance(r.recommendation, Recommendation)

    # Judge produced a final decision anchored on the mean score.
    assert report.decision.mean_weighted_score is not None
    assert isinstance(report.decision.accepted, bool)

    # Author identity was redacted before review.
    assert report.redacted_items

    # Report renders.
    md = report.to_markdown()
    assert "Peer Review Report" in md
    assert "Final Decision" in md
    assert report.to_json()


def test_local_only_rejects_cloud_provider():
    import pytest

    from manuscript_reviewer.config import load_config

    cfg = load_config()
    cfg.roles["reviewer"].provider = "openai"
    cfg.local_only = True
    with pytest.raises(ValueError):
        cfg.assert_privacy()
