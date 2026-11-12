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

Multi-line constructs are converted too: {code}/{noformat} blocks become
fenced blocks (content verbatim, never inline-converted) and wiki tables
become Markdown tables. The (/) (x) (?) status emoticons become emoji, so the
result is not ASCII: print it with UTF-8 output (PYTHONUTF8=1), because
Windows' default cp1252 console raises UnicodeEncodeError on them.
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
_ATTACHMENT_RE = re.compile(r"\[\^([^\]\n]+)\]")
_IMAGE_RE = re.compile(r"!([^!\s][^!\n]*)!")
# (x) is the only one that can also be ordinary prose or code, like f(x), so it
# must stand apart from word characters; (/) and (?) are routinely typed
# straight after a word ("email(/)").
_EMOTICON_RE = re.compile(r"\((?:/|\?)\)|(?<!\w)\(x\)(?!\w)")
_EMOTICONS = {"(/)": "✅", "(x)": "❌", "(?)": "❓"}
_UNDERLINE_RE = re.compile(r'\+([^\s+"][^+\n"]*[^\s+"]|[^\s+"])\+')
_BOLD_RE = re.compile(r'\*([^\s*"][^*\n"]*[^\s*"]|[^\s*"])\*')
_PLACEHOLDER = "\x00{}\x00"

# A {code}/{noformat} block is lifted out of the text before the line-by-line
# pass, so its content is never inline-converted, leaving a placeholder line
# that is swapped for the fenced block at the very end.
_CODE_BLOCK_RE = re.compile(r"[ \t]*\{(code|noformat)(?::([^}\n]*))?\}(.*?)\{\1\}[ \t]*", re.DOTALL)
_CODE_LANGUAGE_RE = re.compile(r"[\w#+.-]+")
_BLOCK_PLACEHOLDER = "\x01{}\x01"
_BLOCK_LINE_RE = re.compile(r"\x01\d+\x01")
_TABLE_SEPARATOR_RE = re.compile(r"(\|\|?)")
# Spans whose "|" belongs to the span rather than the table: [text|url] links,
# !image.png|thumbnail! images and {{monospace}}. Their pipes are swapped for a
# guard character while the row is split into cells.
_TABLE_PIPE_SPAN_RE = re.compile(r"\[[^\[\]\n]*\]|(?<!\w)![^!\s|][^!\n]*!|\{\{.+?\}\}")
_PIPE_GUARD = "\x02"


def to_markdown(text):
    """Convert one JIRA wiki-markup string into Markdown. None stays None."""
    if text is None:
        return None
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = []
    lines = _stash_code_blocks(text, blocks).split("\n")
    out = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("|"):
            rows, i = _collect_table(lines, i)
            _append_block(out, _render_table(rows), lines[i:i + 1])
        elif _BLOCK_LINE_RE.fullmatch(lines[i]):
            _append_block(out, [lines[i]], lines[i + 1:i + 2])
            i += 1
        else:
            out.append(_convert_line(lines[i]))
            i += 1
    result = "\n".join(out)
    for n, block in enumerate(blocks):
        result = result.replace(_BLOCK_PLACEHOLDER.format(n), block)
    return result


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
    line = _ATTACHMENT_RE.sub(lambda m: stash(f"_(attachment: {m.group(1)})_"), line)
    line = _IMAGE_RE.sub(lambda m: stash(f"_(image: {m.group(1)})_"), line)
    line = _EMOTICON_RE.sub(lambda m: _EMOTICONS[m.group(0)], line)
    line = _BOLD_RE.sub(r"**\1**", line)
    line = _UNDERLINE_RE.sub(r"**\1**", line)

    for i, value in enumerate(protected):
        line = line.replace(_PLACEHOLDER.format(i), value)

    return line


def _stash_code_blocks(text, blocks):
    def stash(match):
        kind, params, body = match.groups()
        blocks.append(_fenced(body, _code_language(kind, params)))
        # JIRA renders the block on its own lines even when it sits mid-line
        before = "" if match.start() == 0 or text[match.start() - 1] == "\n" else "\n"
        after = "" if match.end() == len(text) or text[match.end()] == "\n" else "\n"
        return f"{before}{_BLOCK_PLACEHOLDER.format(len(blocks) - 1)}{after}"

    return _CODE_BLOCK_RE.sub(stash, text)


def _code_language(kind, params):
    # {code:java} or {code:java|title=Foo}; a "title=..." parameter is not a language
    first = (params or "").split("|")[0].strip()
    return first if kind == "code" and _CODE_LANGUAGE_RE.fullmatch(first) else ""


def _fenced(body, language):
    body = body.strip("\n")
    fence = "```"
    while fence in body:
        fence += "`"
    return f"{fence}{language}\n{body}\n{fence}"


def _append_block(out, block_lines, upcoming):
    """Append a table or fenced block, set off by blank lines so it renders as its own block."""
    if out and out[-1].strip():
        out.append("")
    out.extend(block_lines)
    if upcoming and upcoming[0].strip():
        out.append("")


def _collect_table(lines, i):
    """Gather the table rows starting at lines[i]; return (rows, index after the table).

    A row whose line doesn't end with "|" is a multi-line cell and carries on
    over the following lines until one does, or a blank line / the next row.
    """
    rows = []
    while i < len(lines) and lines[i].startswith("|"):
        row = lines[i].rstrip()
        i += 1
        while not row.endswith("|") and i < len(lines) and lines[i].strip() and not lines[i].startswith("|"):
            row += "\n" + lines[i].rstrip()
            i += 1
        rows.append(row)
    return rows, i


def _render_table(raw_rows):
    rows = [row for row in map(_split_table_row, raw_rows) if row]
    if not rows:
        return raw_rows
    # Markdown needs a header row: use the first row when JIRA marks all its
    # cells as headers ("||"), otherwise leave the header empty.
    has_header = all(is_header for is_header, _ in rows[0])
    width = max(len(row) for row in rows)
    rows = [row + [(False, "")] * (width - len(row)) for row in rows]
    header = [text for _, text in rows[0]] if has_header else [""] * width
    lines = [_table_line(header), _table_line(["---"] * width)]
    for row in rows[1 if has_header else 0:]:
        lines.append(_table_line([_bold_cell(text) if is_header else text for is_header, text in row]))
    return lines


def _bold_cell(text):
    already_bold = text.startswith("**") and text.endswith("**")
    return text if not text or already_bold else f"**{text}**"


def _table_line(cells):
    return "| " + " | ".join(cells) + " |"


def _split_table_row(row):
    guarded = _TABLE_PIPE_SPAN_RE.sub(lambda m: m.group(0).replace("|", _PIPE_GUARD), row)
    parts = _TABLE_SEPARATOR_RE.split(guarded)
    cells = [(sep == "||", content) for sep, content in zip(parts[1::2], parts[2::2])]
    if cells and cells[-1][1] == "":  # the closing separator, not a cell
        cells.pop()
    return [(is_header, _convert_cell(content)) for is_header, content in cells]


def _convert_cell(content):
    lines = [line.strip() for line in content.replace(_PIPE_GUARD, "|").split("\n")]
    text = "<br>".join(_convert_line(line) for line in lines if line)
    return text.replace("\\\\", "<br>").replace("|", "\\|")
