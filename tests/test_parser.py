import pytest
from story_parser import parse_story_text


def test_extracts_labelled_title():
    result = parse_story_text("Title: Fix login bug\nDescription: Users cannot log in")
    assert result["title"] == "Fix login bug"


def test_extracts_summary_label_as_title():
    result = parse_story_text("Summary: Reset password flow")
    assert result["title"] == "Reset password flow"


def test_falls_back_to_first_line_when_no_label():
    result = parse_story_text("Fix login bug\nSome description text")
    assert result["title"] == "Fix login bug"


def test_extracts_description():
    result = parse_story_text("Title: X\nDescription: Users need to reset their password")
    assert result["description"] == "Users need to reset their password"


def test_extracts_acceptance_criteria():
    text = "Title: X\nDescription: Desc\nAcceptance Criteria:\n- Given a logged in user\n- When they click reset"
    result = parse_story_text(text)
    assert result["acceptance_criteria"] is not None
    assert "Given" in result["acceptance_criteria"]


def test_extracts_ac_short_label():
    text = "Title: X\nAC:\n- User sees confirmation"
    result = parse_story_text(text)
    assert result["acceptance_criteria"] is not None


def test_extracts_story_points():
    result = parse_story_text("Title: X\nStory Points: 5")
    assert result["story_points"] == 5


def test_extracts_story_points_short_label():
    result = parse_story_text("Title: X\nSP: 3")
    assert result["story_points"] == 3


def test_extracts_components():
    result = parse_story_text("Title: X\nComponent: Service center, Auth")
    assert result["components"] == ["Service center", "Auth"]


def test_returns_none_for_missing_fields():
    result = parse_story_text("Just a plain sentence with no labels")
    assert result["description"] is None
    assert result["acceptance_criteria"] is None
    assert result["story_points"] is None
    assert result["components"] is None


def test_empty_input_returns_all_none():
    result = parse_story_text("")
    assert result["title"] is None
    assert result["description"] is None


def test_whitespace_only_input():
    result = parse_story_text("   \n\n   ")
    assert result["title"] is None
