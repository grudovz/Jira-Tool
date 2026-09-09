"""
Convert JIRA wiki markup (as returned by the REST API in description/comment
bodies) into standard Markdown, so it renders as headings/bold/lists instead
of showing raw tokens or breaking CommonMark rendering in chat.

Pure regex-based, no network calls. Deliberately conservative: JIRA's
single-dash strikethrough is left untouched, since it's indistinguishable
from ordinary hyphenated words/compound terms without much richer parsing.
Bold/underline spans require non-whitespace, non-quote boundary characters,
so stray literal asterisks/pluses in prose (e.g. a German "Impressum*"
mandatory-field marker) are left as-is rather than misread as markup.
"""
import re

_HEADER_RE = re.compile(r"^h[1-6]\.\s*(.*)$")
_BULLET_RE = re.compile(r"^(\s*)(\*{1,6})\s+(.*)$")
_COLOR_RE = re.compile(r"\{color:[^}]*\}(.*?)\{color\}")
_ESCAPED_BOLD_RE = re.compile(r"\{\*\}(.+?)\{\*\}")
_MONOSPACE_RE = re.compile(r"\{\{(.+?)\}\}")
_PIPED_LINK_RE = re.compile(r"\[([^|\[\]]+)\|([^\]]+)\]")
_BARE_LINK_RE = re.compile(r"\[(https?://[^\]]+)\]")
_MENTION_RE = re.compile(r"\[~([^\]]+)\]")
_IMAGE_RE = re.compile(r"!([^!\s][^!\n]*)!")
_UNDERLINE_RE = re.compile(r'\+([^\s+"][^+\n"]*[^\s+"]|[^\s+"])\+')
_BOLD_RE = re.compile(r'\*([^\s*"][^*\n"]*[^\s*"]|[^\s*"])\*')
_PLACEHOLDER = "\x00{}\x00"


def to_markdown(text):
    """Convert one JIRA wiki-markup string into Markdown. None stays None."""
    if text is None:
        return None
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(_convert_line(line) for line in text.split("\n"))


def _convert_line(line):
    header_match = _HEADER_RE.match(line)
    if header_match:
        return f"**{_inline(header_match.group(1))}**"

    bullet_match = _BULLET_RE.match(line)
    if bullet_match:
        indent = "  " * (len(bullet_match.group(2)) - 1)
        return f"{indent}- {_inline(bullet_match.group(3))}"

    return _inline(line)


def _inline(line):
    # Tokens whose own content could contain characters (`+`, `*`) that the
    # later bold/underline passes would misread as markup — e.g. a URL like
    # ".../ALP+Feature+Flags+Documentation" — are swapped for an opaque
    # placeholder and restored only after bold/underline have run.
    protected = []

    def stash(value):
        protected.append(value)
        return _PLACEHOLDER.format(len(protected) - 1)

    line = _ESCAPED_BOLD_RE.sub(lambda m: stash(f"**{m.group(1)}**"), line)
    line = _COLOR_RE.sub(r"\1", line)
    line = _MONOSPACE_RE.sub(lambda m: stash(f"`{m.group(1)}`"), line)
    line = _PIPED_LINK_RE.sub(lambda m: stash(f"[{m.group(1)}]({m.group(2)})"), line)
    line = _BARE_LINK_RE.sub(lambda m: stash(f"<{m.group(1)}>"), line)
    line = _MENTION_RE.sub(lambda m: stash(f"@{m.group(1)}"), line)
    line = _IMAGE_RE.sub(lambda m: stash(f"_(image: {m.group(1)})_"), line)
    line = _BOLD_RE.sub(r"**\1**", line)
    line = _UNDERLINE_RE.sub(r"**\1**", line)

    for i, value in enumerate(protected):
        line = line.replace(_PLACEHOLDER.format(i), value)

    return line
