"""
Alias lookup for the `epic:` field line in pasted issue text (`feature:` is
also accepted, since story_parser.py treats it as an alias for the same field).

Typing exact epic keys (e.g. LPDA-2149) is error-prone via dictation, so
the user can dictate a short, memorable epic name instead (e.g. "mail
service") and have it resolved to the real key before parsing. Only the
value of the first `epic:`/`feature:` field line is resolved — text
elsewhere in the pasted issue (summary, description) is left untouched,
since the same words could legitimately appear there as prose.

Edit EPIC_ALIASES to add, change, or remove pairs — no other code changes
needed. Format: {"<name>": "<epic key>"}. Matching is exact (whole value,
case-insensitive) — "epic: mail service" resolves, but "epic: mail
service for Q3" does not, since it's no longer just the alias.
"""
import re

EPIC_ALIASES = {
    "mail service": "LPDA-2149",
    "Israel": "LPDA-1777",
    "Bistro Connect": "LPDA-3064",
}

_LOOKUP = {name.strip().casefold(): key for name, key in EPIC_ALIASES.items()}

_EPIC_LINE = re.compile(r"^(\s*(?:epic|feature)\s*:\s*)(.*)$", re.IGNORECASE | re.MULTILINE)


def resolve_epic_alias(text: str) -> str:
    """Replace a known alias in the first `epic:` field line's value with its epic key."""
    if not text:
        return text

    def _replace(match: "re.Match[str]") -> str:
        prefix, value = match.group(1), match.group(2)
        resolved = _LOOKUP.get(value.strip().casefold())
        return prefix + resolved if resolved else match.group(0)

    return _EPIC_LINE.sub(_replace, text, count=1)
