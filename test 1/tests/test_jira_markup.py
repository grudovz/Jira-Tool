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


def test_code_block_becomes_fenced_block_with_language():
    text = "Example:\n{code:java}\nfoo {\n  bar\n}\n{code}\nafter"
    assert to_markdown(text) == "Example:\n\n```java\nfoo {\n  bar\n}\n```\n\nafter"


def test_code_block_without_language():
    assert to_markdown("{code}\nplain\n{code}") == "```\nplain\n```"


def test_code_block_title_parameter_is_not_a_language():
    text = "{code:title=Foo.java|borderStyle=solid}\nx\n{code}"
    assert to_markdown(text) == "```\nx\n```"


def test_code_block_language_before_other_parameters():
    assert to_markdown("{code:json|title=Payload}\n{}\n{code}") == "```json\n{}\n```"


def test_code_block_closing_tag_on_last_content_line():
    text = "{code:java}\nrating\nnumberOfRatings{code}\nnext"
    assert to_markdown(text) == "```java\nrating\nnumberOfRatings\n```\n\nnext"


def test_code_block_keeps_leading_indentation():
    text = '{code}\n {\n    "a": 1\n }\n{code}'
    assert to_markdown(text) == '```\n {\n    "a": 1\n }\n```'


def test_code_block_content_is_not_inline_converted():
    text = "{code}\n*not bold* {{x}} [~someone] (/)\n{code}"
    assert to_markdown(text) == "```\n*not bold* {{x}} [~someone] (/)\n```"


def test_code_block_with_backticks_gets_longer_fence():
    assert to_markdown("{code}\nuse ``` here\n{code}") == "````\nuse ``` here\n````"


def test_code_block_mid_line_moves_onto_its_own_lines():
    assert to_markdown("see {code}x{code} here") == "see\n\n```\nx\n```\n\nhere"


def test_two_code_blocks_each_restored_in_place():
    text = "{code}\none\n{code}\nbetween\n{code}\ntwo\n{code}"
    assert to_markdown(text) == "```\none\n```\n\nbetween\n\n```\ntwo\n```"


def test_unclosed_code_tag_is_left_alone():
    assert to_markdown("{code}\nnever closed") == "{code}\nnever closed"


def test_noformat_block_becomes_fenced_block():
    assert to_markdown("{noformat}\nraw *text*\n{noformat}") == "```\nraw *text*\n```"


def test_table_becomes_markdown_table():
    text = "||#||Check||\n|1|Works|\n|2|Fails|"
    assert to_markdown(text) == "| # | Check |\n| --- | --- |\n| 1 | Works |\n| 2 | Fails |"


def test_table_is_set_off_from_surrounding_text():
    text = "Before\n||a||b||\n|1|2|\nAfter"
    assert to_markdown(text) == "Before\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n\nAfter"


def test_table_without_header_row_gets_an_empty_header():
    assert to_markdown("|a|b|\n|c|d|") == "|  |  |\n| --- | --- |\n| a | b |\n| c | d |"


def test_table_short_rows_are_padded_to_the_widest_row():
    text = "||a||b||c||\n|1|2|"
    assert to_markdown(text) == "| a | b | c |\n| --- | --- | --- |\n| 1 | 2 |  |"


def test_table_header_cells_in_body_rows_are_bold():
    text = "||Name|Bob|\n||Age|30|"
    assert to_markdown(text) == "|  |  |\n| --- | --- |\n| **Name** | Bob |\n| **Age** | 30 |"


def test_second_header_row_is_not_double_bolded():
    text = "||a||b||\n||*c*||*d*||"
    assert to_markdown(text) == "| a | b |\n| --- | --- |\n| **c** | **d** |"


def test_table_cells_are_converted_inline():
    text = "||Check||Result||\n|*Login*|(/) Pass|\n|[Docs|https://x.io]|(x) Fail|"
    assert to_markdown(text) == (
        "| Check | Result |\n| --- | --- |\n"
        "| **Login** | ✅ Pass |\n"
        "| [Docs](https://x.io) | ❌ Fail |"
    )


def test_table_image_option_pipe_stays_inside_its_cell():
    text = "||a||b||\n|!shot.png|thumbnail!|ok|"
    assert to_markdown(text) == "| a | b |\n| --- | --- |\n| _(image: shot.png\\|thumbnail)_ | ok |"


def test_table_forced_line_break_in_cell():
    text = "||a||b||\n|one\\\\two|x|"
    assert to_markdown(text) == "| a | b |\n| --- | --- |\n| one<br>two | x |"


def test_table_multi_line_cell_is_joined_with_line_breaks():
    text = "||a||b||\n|first\nsecond|x|"
    assert to_markdown(text) == "| a | b |\n| --- | --- |\n| first<br>second | x |"


def test_lone_pipe_line_is_left_alone():
    assert to_markdown("|") == "|"


def test_status_emoticons_become_emoji():
    assert to_markdown("(/) Pass") == "✅ Pass"
    assert to_markdown("(x) Fail") == "❌ Fail"
    assert to_markdown("(?) Can't verify") == "❓ Can't verify"


def test_x_emoticon_inside_a_word_is_left_alone():
    text = "compute f(x) and handleClick(x) here"
    assert to_markdown(text) == text


def test_check_and_question_emoticons_may_touch_the_previous_word():
    assert to_markdown("email(/) sent") == "email✅ sent"
    assert to_markdown("types.(/)") == "types.✅"
    assert to_markdown("right place(?)") == "right place❓"


def test_emoticon_inside_monospace_is_left_alone():
    assert to_markdown("type {{(/)}} here") == "type `(/)` here"


def test_attachment_reference():
    assert to_markdown("see [^analysis.md] for details") == "see _(attachment: analysis.md)_ for details"


def test_attachment_reference_with_markup_characters_in_name_not_corrupted():
    assert to_markdown("[^my*file*+x+.md]") == "_(attachment: my*file*+x+.md)_"
