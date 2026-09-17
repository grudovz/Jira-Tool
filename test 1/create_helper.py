"""
Chains the existing /create parsing steps into a single call:
resolve_epic_alias -> parse_issue -> capitalize_paragraphs -> bold_headings ->
(if Bug) parse_bug_description.

Each step is an existing function from epic_aliases.py, story_parser.py,
capitalization.py, heading_formatting.py, and bug_parser.py — this module only
calls them, it doesn't reimplement or change their behavior.
"""
import json
import sys

from epic_aliases import resolve_epic_alias
from story_parser import parse_issue
from capitalization import capitalize_paragraphs
from heading_formatting import bold_headings
from bug_parser import parse_bug_description


def prepare_issue(raw_text: str) -> dict:
    """
    Returns the parsed issue fields plus a `bug_format_applied` flag:
    - True: issue_type is Bug and the description was reformatted
    - False: issue_type is Bug but the description didn't match the expected
      Steps/blank-line/expected-result shape, so it was left as parsed (capitalized only)
    - None: issue_type is not Bug, no reformat attempted
    """
    parsed = parse_issue(resolve_epic_alias(raw_text))

    if parsed.get("summary") is not None:
        parsed["summary"] = capitalize_paragraphs(parsed["summary"])
    if parsed.get("description") is not None:
        parsed["description"] = capitalize_paragraphs(parsed["description"])
        parsed["description"] = bold_headings(parsed["description"])

    bug_format_applied = None
    if (parsed.get("issue_type") or "").lower() == "bug" and parsed.get("description") is not None:
        reformatted = parse_bug_description(parsed["description"])
        if reformatted is not None:
            parsed["description"] = reformatted
            bug_format_applied = True
        else:
            bug_format_applied = False

    parsed["bug_format_applied"] = bug_format_applied
    return parsed


if __name__ == "__main__":
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        raw = f.read()
    print(json.dumps(prepare_issue(raw), indent=2))
