from manuscript_reviewer.ingestion import parse_manuscript, redact_identity


def test_parse_extracts_sections(sample_text):
    m = parse_manuscript(sample_text, is_text=True)
    assert "Attention-Guided Sparse Routing" in m.title
    assert "mixture-of-experts" in m.abstract.lower()
    assert "Shazeer" in m.references
    assert m.body


def test_redaction_removes_author_block_and_emails(sample_text):
    m = parse_manuscript(sample_text, is_text=True)
    redacted = redact_identity(m)
    assert "jane.researcher@example.edu" not in redacted.full_text
    assert "alan@example.edu" not in redacted.full_text
    assert "[AUTHOR IDENTITY REDACTED]" in redacted.full_text
    assert redacted.redacted_identity  # something was removed
    # Author names should no longer appear in the body sent to the model.
    assert "Maria Sample" not in redacted.full_text


def test_redaction_strips_acknowledgements(sample_text):
    m = parse_manuscript(sample_text, is_text=True)
    redacted = redact_identity(m)
    assert "Grant #12345" not in redacted.full_text
