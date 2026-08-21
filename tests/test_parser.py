import pytest
from story_parser import parse_issue


def test_summary_is_first_line():
    result = parse_issue("Fix login bug\nissue: Bug")
    assert result["summary"] == "Fix login bug"


def test_full_example_with_all_fields():
    text = (
        "Fix login bug\n"
        "issue: Bug\n"
        "epic: LPDA-1777\n"
        "component: Service center\n"
        "points: 4\n"
        "Users cannot log in when their session expires.\n"
        "This happens on both mobile and desktop."
    )
    result = parse_issue(text)
    assert result["summary"] == "Fix login bug"
    assert result["issue_type"] == "Bug"
    assert result["epic_link"] == "LPDA-1777"
    assert result["component"] == "Service center"
    assert result["story_points"] == 4
    assert result["description"] == (
        "Users cannot log in when their session expires.\nThis happens on both mobile and desktop."
    )


def test_labels_are_case_insensitive():
    text = "Fix login bug\nIssue: Bug\nEPIC: LPDA-1777"
    result = parse_issue(text)
    assert result["issue_type"] == "Bug"
    assert result["epic_link"] == "LPDA-1777"


def test_missing_fields_return_none():
    text = "Fix login bug\ncomponent: Service center\nDescription text here"
    result = parse_issue(text)
    assert result["issue_type"] is None
    assert result["epic_link"] is None
    assert result["story_points"] is None
    assert result["component"] == "Service center"
    assert result["description"] == "Description text here"


def test_description_immediately_after_summary_when_no_fields():
    result = parse_issue("Fix login bug\nUsers cannot log in.")
    assert result["summary"] == "Fix login bug"
    assert result["description"] == "Users cannot log in."
    assert result["issue_type"] is None


def test_summary_only_no_description():
    result = parse_issue("Fix login bug")
    assert result["summary"] == "Fix login bug"
    assert result["description"] is None


def test_story_points_extracts_digits():
    result = parse_issue("Fix login bug\npoints: 8\nDesc")
    assert result["story_points"] == 8


def test_description_preserves_internal_blank_lines():
    text = "Fix login bug\nissue: Bug\nFirst paragraph.\n\nSecond paragraph."
    result = parse_issue(text)
    assert result["description"] == "First paragraph.\n\nSecond paragraph."


def test_empty_input_returns_all_none():
    result = parse_issue("")
    assert result["summary"] is None
    assert result["description"] is None
    assert result["issue_type"] is None
    assert result["epic_link"] is None
    assert result["component"] is None
    assert result["story_points"] is None


def test_whitespace_only_input():
    result = parse_issue("   \n\n   ")
    assert result["summary"] is None
