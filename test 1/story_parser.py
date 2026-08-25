"""
Parser for pasted issue text in a fixed, dictation-friendly layout:

    <summary>
    issue: <value>          (optional)
    epic: <value>           (optional, "feature:" is also accepted)
    component: <value>      (optional)
    points: <value>         (optional)
    <description — everything else, may span multiple lines>

The first line is always the summary. Any field lines must come immediately
after it, each on its own line as "label: value". The first line that isn't
a recognised field line starts the description block, which runs to the end
of the text.

Fields not found are returned as None. This module has no knowledge of
jira_client's defaults (e.g. DEFAULT_EPIC_LINK) — callers should omit None
values when forwarding to create_issue/update_issue so those defaults apply.
"""
import re

_FIELD_PATTERNS = {
    "issue_type": re.compile(r"^issue\s*:\s*(.*)$", re.IGNORECASE),
    "epic_link": re.compile(r"^(?:epic|feature)\s*:\s*(.*)$", re.IGNORECASE),
    "component": re.compile(r"^component\s*:\s*(.*)$", re.IGNORECASE),
    "story_points": re.compile(r"^points?\s*:\s*(.*)$", re.IGNORECASE),
}


def parse_issue(raw_text: str) -> dict:
    """
    Parse pasted issue text into structured fields.

    Returns a dict with keys:
        summary, issue_type, epic_link, component, story_points, description
    Any field not found in the text will be None.
    """
    text = raw_text.strip()
    result: dict[str, "str | int | None"] = {
        "summary": None,
        "issue_type": None,
        "epic_link": None,
        "component": None,
        "story_points": None,
        "description": None,
    }

    if not text:
        return result

    lines = text.splitlines()
    result["summary"] = lines[0].strip() or None

    # Consume field lines directly after the summary; stop at the first line that isn't one.
    idx = 1
    while idx < len(lines):
        line = lines[idx].strip()
        if not line:
            idx += 1
            continue

        matched_field = None
        value = None
        for field, pattern in _FIELD_PATTERNS.items():
            match = pattern.match(line)
            if match:
                matched_field = field
                value = match.group(1).strip()
                break

        if not matched_field:
            break

        if matched_field == "story_points":
            digits = re.search(r"\d+", value) if value else None
            result["story_points"] = int(digits.group()) if digits else None
        else:
            result[matched_field] = value or None
        idx += 1

    description = "\n".join(lines[idx:]).strip()
    result["description"] = description or None

    return result
