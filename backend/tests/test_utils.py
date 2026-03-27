"""
Tests for utility functions in openedx_ai_extensions.
"""

from openedx_ai_extensions.utils import is_generator, normalize_input_to_text


def test_normalize_input_to_text_with_string():
    assert normalize_input_to_text("hello") == "hello"


def test_normalize_input_to_text_with_dict_text_key():
    assert normalize_input_to_text({"text": "hello"}) == "hello"


def test_normalize_input_to_text_with_dict_no_text_key():
    # It returns an empty string because it uses .get("text") or ""
    assert normalize_input_to_text({"other": "value"}) == ""


def test_normalize_input_to_text_with_none():
    assert normalize_input_to_text(None) == ""


def test_normalize_input_to_text_with_other_type():
    assert normalize_input_to_text(123) == "123"


def test_is_generator():
    def my_gen():
        yield 1

    gen = my_gen()
    assert is_generator(gen) is True
    assert is_generator([1, 2, 3]) is False
    assert is_generator(123) is False
