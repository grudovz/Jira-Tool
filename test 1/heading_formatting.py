"""
Bolds known JIRA description section headings (Background, Design, Technical
Details, Acceptance Criteria/AC) when one appears as the first line of a
paragraph, per the Description structure convention in copilot-instructions.md.

A "paragraph" is the same unit capitalization.py uses: a block of text
separated from its neighbors by one or more blank lines. Only the heading
line itself is wrapped in JIRA bold markup (*Heading*); the rest of the
paragraph is left untouched.
"""
import re

_HEADINGS = ("Background", "Design", "Technical Details", "Acceptance Criteria", "AC")
_HEADING_LINE = re.compile(
    r"^(" + "|".join(re.escape(h) for h in _HEADINGS) + r")\s*:?\s*$",
    re.IGNORECASE,
)
_PARAGRAPH_SPLIT = re.compile(r"(\n\s*\n)")


def bold_headings(text: str) -> str:
    """Wrap a recognised section heading in JIRA bold markup when it starts its own paragraph."""
    if not text:
        return text

    parts = _PARAGRAPH_SPLIT.split(text)
    for i in range(0, len(parts), 2):
        parts[i] = _bold_first_line(parts[i])
    return "".join(parts)


def _bold_first_line(paragraph: str) -> str:
    lines = paragraph.split("\n", 1)
    first_line = lines[0].strip()
    match = _HEADING_LINE.match(first_line)
    if not match:
        return paragraph
    bolded = f"*{match.group(1)}*"
    return bolded if len(lines) == 1 else f"{bolded}\n{lines[1]}"
