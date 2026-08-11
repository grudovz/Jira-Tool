"""
Rule-based parser for pasted story text.
No LLM dependency — works fully offline.
Recognises common heading patterns: Title/Summary, Description, Acceptance Criteria, Story Points, Component.
Falls back gracefully when a section is absent.
"""
import re


def parse_story_text(raw_text: str) -> dict:
    """
    Parse a block of pasted text into structured story fields.

    Returns a dict with keys:
        title, description, acceptance_criteria, story_points, components
    Any field not found in the text will be None.
    """
    text = raw_text.strip()
    result = {
        "title": None,
        "description": None,
        "acceptance_criteria": None,
        "story_points": None,
        "components": None,
    }

    if not text:
        return result

    # -- Title --
    # Look for an explicit label first; fall back to the first non-empty line.
    title_match = re.search(r"(?:Title|Summary)\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if title_match:
        result["title"] = title_match.group(1).strip()
    else:
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), None)
        result["title"] = first_line

    # -- Description --
    # Everything after "Description:" up to the next recognised section heading.
    desc_match = re.search(
        r"Description\s*[:\-]\s*(.*?)(?=\n\s*(?:Acceptance Criteria|AC|Story Points?|SP|Component)|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if desc_match:
        value = desc_match.group(1).strip()
        result["description"] = value or None

    # -- Acceptance Criteria --
    ac_match = re.search(
        r"(?:Acceptance Criteria|AC)\s*[:\-]\s*(.*?)(?=\n\s*(?:Story Points?|SP|Component)|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if ac_match:
        value = ac_match.group(1).strip()
        result["acceptance_criteria"] = value or None

    # -- Story Points --
    sp_match = re.search(r"(?:Story Points?|SP)\s*[:\-]?\s*(\d+)", text, re.IGNORECASE)
    if sp_match:
        result["story_points"] = int(sp_match.group(1))

    # -- Components --
    comp_match = re.search(r"Components?\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if comp_match:
        result["components"] = [c.strip() for c in comp_match.group(1).split(",") if c.strip()]

    return result
