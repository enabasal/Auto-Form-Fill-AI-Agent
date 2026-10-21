import pytest

from autoformfill.llm import LLMError, parse_json_object


def test_plain_json():
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_code_fence_and_chatter():
    assert parse_json_object('Sure!\n```json\n{"a": [1, 2]}\n```') == {"a": [1, 2]}


@pytest.mark.parametrize("bad", ["", "no json here", "[1, 2]", "{broken"])
def test_bad_output_raises(bad):
    with pytest.raises(LLMError):
        parse_json_object(bad)
