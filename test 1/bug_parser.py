"""
Parser for a bug report's description block, in a fixed, dictation-friendly layout:

    Steps
    <step 1>
    <step 2>
    ...
    <blank line>
    <expected result — everything after the blank line, may span multiple lines>

The first non-blank line must be a "Steps" header (case-insensitive, optional
trailing colon). Each following line up to the first blank line is one step.
The blank line is required — it's what separates the steps from the expected
result.

This transforms that raw block into the JIRA-formatted description structure
used for bug reports: a "Tested in version" line, a bold *Steps* section as a
numbered list, and a bold *Expected result:* section.

If the input doesn't match this shape, parse_bug_description returns None —
same "don't invent, signal absence" philosophy as story_parser.parse_issue.
"""
import re

DEFAULT_APP_VERSION = "1.8.0"  # current application version — update when the user gives a new one

_STEPS_HEADER = re.compile(r"^steps\s*:?\s*$", re.IGNORECASE)


def parse_bug_description(raw_description: str, version: str = DEFAULT_APP_VERSION) -> "str | None":
    """
    Parse a raw bug description block and assemble the final JIRA-formatted text.

    Returns None if the input doesn't start with a recognisable "Steps" header
    or has no blank-line separator before the expected result.
    """
    if not raw_description:
        return None

    lines = raw_description.strip("\n").splitlines()
    if not lines or not _STEPS_HEADER.match(lines[0].strip()):
        return None

    idx = 1
    steps = []
    while idx < len(lines) and lines[idx].strip():
        steps.append(lines[idx].strip())
        idx += 1

    if not steps:
        return None

    # idx is now at the blank line separator; it must exist and be followed by content.
    if idx >= len(lines):
        return None
    idx += 1  # skip the blank line
    expected_result = "\n".join(lines[idx:]).strip()
    if not expected_result:
        return None

    numbered_steps = "\n".join(f"{i}) {step}" for i, step in enumerate(steps, start=1))

    return (
        f"Tested in version: {version}\n\n"
        f"*Steps*\n\n{numbered_steps}\n\n"
        f"*Expected result:*\n\n{expected_result}"
    )
