from manuscript_reviewer.llm.base import extract_json


def test_extract_plain_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_fenced_json():
    text = 'Here you go:\n```json\n{"a": 2, "b": "x"}\n```\nThanks!'
    assert extract_json(text) == {"a": 2, "b": "x"}


def test_extract_embedded_json():
    text = 'blah {"nested": {"k": [1, 2]}} trailing'
    assert extract_json(text) == {"nested": {"k": [1, 2]}}


def test_extract_raises_on_garbage():
    import pytest

    with pytest.raises(ValueError):
        extract_json("no json here")
