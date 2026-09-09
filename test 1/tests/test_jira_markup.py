import pytest
from jira_markup import to_markdown


def test_none_stays_none():
    assert to_markdown(None) is None


def test_headers():
    assert to_markdown("h1. Title") == "**Title**"
    assert to_markdown("h3. Sub heading") == "**Sub heading**"


def test_top_level_bullet():
    assert to_markdown(" * item one") == "- item one"


def test_nested_bullet_indents():
    text = " * top\n ** nested"
    assert to_markdown(text) == "- top\n  - nested"


def test_bold_asterisk():
    assert to_markdown("*As a traveller,*") == "**As a traveller,**"


def test_mid_line_bold():
    text = "Video button is displayed *only when configured* for the offer."
    assert to_markdown(text) == "Video button is displayed **only when configured** for the offer."


def test_underline_becomes_bold():
    assert to_markdown("+AC+") == "**AC**"


def test_escaped_bold_braces():
    assert to_markdown("use this repo as a {*}reference only{*} please") == \
        "use this repo as a **reference only** please"


def test_monospace():
    assert to_markdown("set {{VITE_FEATURE_FLAG}} to true") == "set `VITE_FEATURE_FLAG` to true"


def test_piped_link():
    text = "[Adobe XD|https://xd.adobe.com/view/abc/]"
    assert to_markdown(text) == "[Adobe XD](https://xd.adobe.com/view/abc/)"


def test_bare_bracket_link():
    text = "[https://example.com/page]"
    assert to_markdown(text) == "<https://example.com/page>"


def test_user_mention():
    assert to_markdown("please check [~zgrudov] on this") == "please check @zgrudov on this"


def test_inline_image_placeholder():
    assert to_markdown("!screenshot.png!") == "_(image: screenshot.png)_"


def test_color_wrapper_is_stripped_not_shown():
    text = "{color:#00875a}looks good{color}"
    assert to_markdown(text) == "looks good"


def test_stray_literal_asterisk_not_treated_as_bold():
    # German "mandatory field" convention (trailing *), not JIRA bold markup.
    text = '"E-Mail-Signatur / Impressum*" section switched positions'
    assert to_markdown(text) == text


def test_two_stray_asterisks_do_not_pair_across_unrelated_text():
    text = '"Impressum*" is the title. -"* Pflichtfeld" is the note below-'
    assert to_markdown(text) == text


def test_strikethrough_left_untouched():
    text = "well-known-issue with hyphenated-words"
    assert to_markdown(text) == text


def test_color_and_bullet_combined():
    text = " * {color:#00875a}Section split with whitespace between them{color}"
    assert to_markdown(text) == "- Section split with whitespace between them"


def test_header_renders_as_bold_line():
    assert to_markdown("h2. Designs") == "**Designs**"


def test_crlf_line_endings_normalized():
    assert to_markdown("h1. Title\r\nnext line") == "**Title**\nnext line"


def test_url_with_literal_plus_signs_not_corrupted():
    text = "[https://example.com/wiki/pages/1/ALP+Feature+Flags+Documentation]"
    assert to_markdown(text) == "<https://example.com/wiki/pages/1/ALP+Feature+Flags+Documentation>"


def test_piped_link_url_with_query_string_not_corrupted():
    text = "[Adobe XD|https://xd.adobe.com/view/abc?a=1+2&b=x*y]"
    assert to_markdown(text) == "[Adobe XD](https://xd.adobe.com/view/abc?a=1+2&b=x*y)"
