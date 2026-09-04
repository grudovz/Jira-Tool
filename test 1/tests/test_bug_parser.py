import pytest
from bug_parser import parse_bug_description, DEFAULT_APP_VERSION


def test_standard_three_step_example():
    text = "Steps\nOpen the app\nClick favourite\nRefresh preview\n\nImage should show in the preview"
    result = parse_bug_description(text)
    assert result == (
        f"Tested in version: {DEFAULT_APP_VERSION}\n\n"
        "*Steps*\n\n"
        "1) Open the app\n"
        "2) Click favourite\n"
        "3) Refresh preview\n\n"
        "*Expected result:*\n\n"
        "Image should show in the preview"
    )


def test_single_step():
    text = "Steps\nOpen the app\n\nIt should load"
    result = parse_bug_description(text)
    assert "1) Open the app" in result
    assert "2)" not in result


def test_multiline_expected_result():
    text = "Steps\nOpen the app\n\nFirst line of expectation.\nSecond line of expectation."
    result = parse_bug_description(text)
    assert result.endswith("First line of expectation.\nSecond line of expectation.")


def test_steps_header_with_colon():
    text = "Steps:\nOpen the app\n\nIt should load"
    result = parse_bug_description(text)
    assert result is not None
    assert "1) Open the app" in result


def test_steps_header_case_insensitive():
    text = "STEPS\nOpen the app\n\nIt should load"
    result = parse_bug_description(text)
    assert result is not None


def test_custom_version_override():
    text = "Steps\nOpen the app\n\nIt should load"
    result = parse_bug_description(text, version="2.0.0")
    assert result.startswith("Tested in version: 2.0.0")


def test_missing_blank_line_separator_returns_none():
    text = "Steps\nOpen the app\nIt should load"
    result = parse_bug_description(text)
    assert result is None


def test_no_steps_header_returns_none():
    text = "Users cannot log in when their session expires."
    result = parse_bug_description(text)
    assert result is None


def test_empty_input_returns_none():
    assert parse_bug_description("") is None


def test_steps_with_no_expected_result_returns_none():
    text = "Steps\nOpen the app\n\n"
    result = parse_bug_description(text)
    assert result is None
