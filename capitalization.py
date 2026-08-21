"""
Capitalizes the first letter of each paragraph in pasted issue text, to
work around voice dictation not auto-capitalizing new sentences.

Only the first alphabetic character of each paragraph is touched — later
sentences within the same paragraph (after a ". ", for instance) are left
exactly as dictated, and a paragraph that doesn't start with a letter
(e.g. a JSON/code block with no lead-in line) is left untouched entirely.
This is deliberate: it avoids mangling lowercase identifiers (e.g.
`packageOffer`, `rating`) in data blocks pasted as their own paragraph.

A "paragraph" is a block of text separated from its neighbors by one or
more blank lines; blank-line separators themselves are preserved as-is.
"""
import re

_PARAGRAPH_SPLIT = re.compile(r"(\n\s*\n)")
_FIRST_LETTER = re.compile(r"[a-zA-Z]")


def capitalize_paragraphs(text: str) -> str:
    """Uppercase the first letter of each paragraph in `text`; leave everything else unchanged."""
    if not text:
        return text

    parts = _PARAGRAPH_SPLIT.split(text)
    for i in range(0, len(parts), 2):
        parts[i] = _capitalize_first_letter(parts[i])
    return "".join(parts)


def _capitalize_first_letter(paragraph: str) -> str:
    match = _FIRST_LETTER.search(paragraph)
    if not match:
        return paragraph
    idx = match.start()
    return paragraph[:idx] + paragraph[idx].upper() + paragraph[idx + 1:]
