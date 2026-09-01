"""
Word substitution glossary for dictated issue text.

Voice dictation in German is unreliable, so issue text is dictated in
English instead, with certain domain terms swapped for their German
equivalents (the terms actually used in the target system) before
parsing. Matching on the English term is case-insensitive and only
matches whole words; the German replacement is inserted exactly as
defined below, regardless of the matched word's casing..

Edit GLOSSARY to add, change, or remove pairs — no other code changes
needed. Format: {"<english term>": "<german replacement>"}.
"""
import re

GLOSSARY = {
    "German agent": "Berater",
    "German form agent": "Reiseberater",
    "German email": "Versenden",
    "German offer transfer": "Angebot Ubertragen",
    "German reviews": "Hotelbewertung",
    "German overview": "Übersicht",
    "German hotel attributes": "Hotelmerkmale",
    "German print": "Drucken",
    "German bookmark": "Merken",
    "German agency data": "Agentur-Daten",
    "German book": "Buchen",
    "German request": "Anfrage",
    "German transfer to bistro": "Nach Bistro übertragen",
}

_PATTERNS = [
    (re.compile(r"\b" + re.escape(english) + r"\b", re.IGNORECASE), german)
    for english, german in sorted(GLOSSARY.items(), key=lambda pair: len(pair[0]), reverse=True)
]


def apply_glossary(text: str) -> str:
    """Replace English glossary terms in `text` with their German equivalents."""
    if not text:
        return text
    for pattern, german in _PATTERNS:
        text = pattern.sub(german, text)
    return text
