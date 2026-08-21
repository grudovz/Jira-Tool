import pytest
from capitalization import capitalize_paragraphs


def test_first_letter_of_single_paragraph_is_capitalized():
    result = capitalize_paragraphs("fix login bug")
    assert result == "Fix login bug"


def test_only_first_sentence_of_paragraph_is_capitalized():
    text = "this is sentence one. this is sentence two."
    result = capitalize_paragraphs(text)
    assert result == "This is sentence one. this is sentence two."


def test_each_paragraph_capitalized_independently():
    text = "first paragraph.\n\nsecond paragraph."
    result = capitalize_paragraphs(text)
    assert result == "First paragraph.\n\nSecond paragraph."


def test_already_capitalized_paragraph_unchanged():
    text = "Already fine."
    assert capitalize_paragraphs(text) == "Already fine."


def test_json_block_with_lead_in_line_is_untouched():
    text = "NLT data:\npackageOffer {\n  rating\n  recommendation\n}"
    assert capitalize_paragraphs(text) == text


def test_json_block_with_no_lead_in_line_gets_its_first_letter_capitalized():
    # Known caveat: without a lead-in line, the field name IS the paragraph's
    # first letter and gets capitalized like any other sentence start.
    text = "packageOffer {\n  rating\n  recommendation\n}"
    result = capitalize_paragraphs(text)
    assert result == "PackageOffer {\n  rating\n  recommendation\n}"


def test_blank_line_separators_are_preserved():
    text = "one paragraph.\n\n\nanother paragraph."
    result = capitalize_paragraphs(text)
    assert result == "One paragraph.\n\n\nAnother paragraph."


def test_empty_input_returns_empty():
    assert capitalize_paragraphs("") == ""


def test_paragraph_with_no_letters_is_unchanged():
    assert capitalize_paragraphs("123456\n\n789") == "123456\n\n789"
