import pytest
from epic_aliases import resolve_epic_alias


def test_known_alias_is_resolved():
    text = "Fix login bug\nepic: mail service\nDescription text."
    result = resolve_epic_alias(text)
    assert "epic: LPDA-2149" in result
    assert "mail service" not in result


def test_matching_is_case_insensitive():
    text = "Fix login bug\nEPIC: Mail Service\nDescription text."
    result = resolve_epic_alias(text)
    assert "EPIC: LPDA-2149" in result


def test_feature_label_is_also_resolved():
    text = "Fix login bug\nfeature: Israel\nDescription text."
    result = resolve_epic_alias(text)
    assert "feature: LPDA-1777" in result
    assert "Israel" not in result


def test_unknown_value_is_left_unchanged():
    text = "Fix login bug\nepic: LPDA-9999\nDescription text."
    result = resolve_epic_alias(text)
    assert "epic: LPDA-9999" in result


def test_partial_match_is_not_resolved():
    text = "Fix login bug\nepic: mail service for Q3\nDescription text."
    result = resolve_epic_alias(text)
    assert "epic: mail service for Q3" in result


def test_only_first_epic_line_is_touched():
    text = "Fix login bug\nepic: mail service\nDescription mentions epic: mail service again."
    result = resolve_epic_alias(text)
    lines = result.splitlines()
    assert lines[1] == "epic: LPDA-2149"
    assert "Description mentions epic: mail service again." in result


def test_no_epic_line_returns_text_unchanged():
    text = "Fix login bug\nDescription text only."
    assert resolve_epic_alias(text) == text


def test_empty_input_returns_empty():
    assert resolve_epic_alias("") == ""
