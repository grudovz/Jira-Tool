---
name: create
description: 'Parse pasted issue text and create a new JIRA issue from it, via story_parser.py and jira_client.py. Use when the user pastes issue text and asks to create a story/issue, or types /create. By default, parses first and shows the result in chat for confirmation before creating anything in JIRA.'
argument-hint: '[pasted issue text]'
---

# Create a JIRA Issue from Pasted Text

## Mode
`AUTO_CREATE: true` — proceeds straight to creating the issue after parsing, no confirmation required. Flip back to `false` if the user wants confirmation again.

## When to Use
- The user pastes issue text and asks to create a story/issue, or types `/create`
- Text follows the fixed layout `story_parser.parse_issue` expects: first line = summary, optional `issue:` / `epic:` / `component:` / `points:` lines directly after it, then the description (see [story_parser.py](../../../test%201/story_parser.py) docstring)
- If `issue: Bug`, the description itself is further expected to follow the `Steps` / step-lines / blank line / expected-result layout (see [bug_parser.py](../../../test%201/bug_parser.py) docstring) — this skill reformats it automatically in step 2

## Procedure
1. **Resolve the raw text**: everything the user pasted/wrote after `/create` (or in the message that triggered this skill). If nothing was pasted, ask for the text to parse.
2. **Parse and prepare the fields** by running the raw text through `prepare_issue` in [create_helper.py](../../../test%201/create_helper.py) — it chains the same existing functions this skill always used (`resolve_epic_alias`, `parse_issue`, `capitalize_paragraphs`, `bold_headings`, and, for bugs, `parse_bug_description`) into one call and returns the fields as JSON, plus a `bug_format_applied` flag (`true` = reformatted, `false` = didn't match the expected shape and was left as parsed, `null` = not a bug). `bold_headings` (in [heading_formatting.py](../../../test%201/heading_formatting.py)) wraps a recognised section heading (Background, Design, Technical Details, Acceptance Criteria/AC) in JIRA bold markup when it starts its own paragraph, per the Description structure convention in copilot-instructions.md. Do not modify `create_helper.py`'s logic beyond what's needed to keep it a thin wrapper — it must keep calling the existing functions unchanged, not reimplement their behavior.
   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe create_helper.py "<path to a temp file containing the raw text>"
   ```
   Write the raw text to a temp file under `$env:TEMP` first if it contains triple-quotes or other characters that break shell quoting (usually the safer default).
   **Known caveat** (from `capitalize_paragraphs`, unchanged by this wrapper): if a paragraph is a JSON/code block with no lead-in prose line (e.g. it starts directly with `packageOffer {`), that first identifier gets capitalized too. If this happens, surface it rather than silently re-lowercasing it.
3. **Show the parsed result in chat** exactly as returned — Summary, Issue Type, Epic Link, Component, Story Points, Description (post-reformat, if `bug_format_applied` is `true`) — before doing anything else. Call out any field that came back `None` and which default will apply if left unset (issue type → "Story", epic link → `DEFAULT_EPIC_LINK`, component → `DEFAULT_COMPONENT` — see [jira_client.py](../../../test%201/jira_client.py)). If `summary` is `None`, stop and ask for text with a usable first line — JIRA requires a summary and there is no default for it. If `bug_format_applied` is `false`, mention that too so the user knows the description wasn't reformatted.
4. **Confirm or create, depending on Mode**:
   - `AUTO_CREATE: false` (default): stop here and ask the user whether to create this issue as parsed, or fix something first. Do not call `create_issue` until they explicitly confirm.
   - `AUTO_CREATE: true`: proceed straight to creating it, still having shown the parsed fields in step 3 for visibility.
5. **Create the issue** via the existing `create_issue` function in [jira_client.py](../../../test%201/jira_client.py) — do not modify that file. Omit any field that parsed as `None` so `create_issue`'s own defaults apply (per `story_parser.py`'s docstring — it has no knowledge of those defaults):
   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe -c "from jira_client import create_issue; i = create_issue(summary='<...>', description='<...>', issue_type='<...>', epic_link='<...>', component='<...>', story_points=<...>); print(i.key)"
   ```
   For anything multi-line or quote-heavy (usually the description), write a small temp script under `$env:TEMP` instead of inlining.
6. **Confirm back** to the user with the created issue key and a link (`<JIRA_URL>/browse/<KEY>`, `JIRA_URL` from [jira_client.py](../../../test%201/jira_client.py)).

## Notes
- Never invent or silently correct parsed field values — if something looks wrong, surface it in step 3 and let the user decide, don't fix it silently.
- **Exception**: don't flag the description's first line repeating the summary verbatim. The user does this deliberately for simple stories — it's a known convention, not a duplication artifact.
- Do not touch `jira_client.py`, `story_parser.py`, `bug_parser.py`, or `coord_finder.py` — only call their existing functions.
- `create_helper.py` is a thin wrapper around those same functions — it exists only to bundle the parse→capitalize→bug-format chain into one call. It's fine to touch, but keep it a wrapper: it must not reimplement or alter the behavior of `parse_issue`, `capitalize_paragraphs`, or `parse_bug_description`.
- `epic_aliases.py` is the exception: its `resolve_epic_alias` function is off-limits like the others, but the `EPIC_ALIASES` dict is meant to be edited directly for new epic name→key pairs.
- `capitalization.py` has no editable data (no dict) — it's off-limits like `story_parser.py`, only call `capitalize_paragraphs`.
- `bug_parser.py`'s `DEFAULT_APP_VERSION` constant is the exception to its own off-limits rule — update it directly when the user gives a new current application version.
- This skill is the create-side counterpart to `/draft` (updates an existing issue's description) and `/comment` (adds a comment) — together they cover the JIRA write paths.
