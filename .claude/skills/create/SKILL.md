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

## Procedure
1. **Resolve the raw text**: everything the user pasted/wrote after `/create` (or in the message that triggered this skill). If nothing was pasted, ask for the text to parse.
2. **Apply the glossary, resolve epic aliases, then parse**: run the raw text through `apply_glossary` in [glossary.py](../../../test%201/glossary.py) first — it swaps English dictation words for their German equivalents (case-insensitive, whole-word match), a workaround since German dictation doesn't work well for the user. Then run it through `resolve_epic_alias` in [epic_aliases.py](../../../test%201/epic_aliases.py) — it resolves a known short name in the `epic:` field line's value (e.g. `epic: mail service`) to its real epic key (e.g. `epic: LPDA-2149`); exact match only (case-insensitive), text elsewhere is untouched. Then parse the result with the existing `parse_issue` function in [story_parser.py](../../../test%201/story_parser.py). Do not modify `story_parser.py`, `apply_glossary`, or `resolve_epic_alias` — the `GLOSSARY` dict in glossary.py and the `EPIC_ALIASES` dict in epic_aliases.py are the exceptions meant to be edited (add/update pairs there when the user gives new ones):
   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe -c "from glossary import apply_glossary; from epic_aliases import resolve_epic_alias; from story_parser import parse_issue; import json; print(json.dumps(parse_issue(resolve_epic_alias(apply_glossary(r'''<RAW_TEXT>'''))), indent=2))"
   ```
   If the text contains triple-quotes or other characters that break PowerShell/Python quoting, write it to a small temp file under `$env:TEMP` and read it back inside the one-liner instead of inlining it.
3. **Capitalize the parsed `summary` and `description` independently** using `capitalize_paragraphs` in [capitalization.py](../../../test%201/capitalization.py) — it uppercases just the first letter of each paragraph (blank-line-separated block), to work around voice dictation not auto-capitalizing new sentences; later sentences within the same paragraph are left as dictated, by design. Run this **after** parsing, on the two already-separated fields (not on the raw text beforehand) — running it on the raw blob first would merge the summary/field-line block with the description's first paragraph whenever there's no blank line between them (the normal case for this tool's fixed layout), so the description's actual first sentence would never get capitalized. Skip a field that's `None`.
   ```powershell
   .\.venv\Scripts\python.exe -c "from capitalization import capitalize_paragraphs; ..."
   ```
   Do not modify `capitalize_paragraphs` — it has no editable data (no dict), unlike glossary.py/epic_aliases.py, so it's fully off-limits like story_parser.py.
   **Known caveat**: if a paragraph is a JSON/code block with no lead-in prose line (e.g. it starts directly with `packageOffer {`), that first identifier gets capitalized too — the function only knows "first letter of the paragraph," not "is this prose or code." If this happens, surface it rather than silently re-lowercasing it.
4. **Show the parsed result in chat** exactly as returned — Summary, Issue Type, Epic Link, Component, Story Points, Description — before doing anything else. Call out any field that came back `None` and which default will apply if left unset (issue type → "Story", epic link → `DEFAULT_EPIC_LINK`, component → `DEFAULT_COMPONENT` — see [jira_client.py](../../../test%201/jira_client.py)). If `summary` is `None`, stop and ask for text with a usable first line — JIRA requires a summary and there is no default for it.
5. **Confirm or create, depending on Mode**:
   - `AUTO_CREATE: false` (default): stop here and ask the user whether to create this issue as parsed, or fix something first. Do not call `create_issue` until they explicitly confirm.
   - `AUTO_CREATE: true`: proceed straight to creating it, still having shown the parsed fields in step 4 for visibility.
6. **Create the issue** via the existing `create_issue` function in [jira_client.py](../../../test%201/jira_client.py) — do not modify that file. Omit any field that parsed as `None` so `create_issue`'s own defaults apply (per `story_parser.py`'s docstring — it has no knowledge of those defaults):
   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe -c "from jira_client import create_issue; i = create_issue(summary='<...>', description='<...>', issue_type='<...>', epic_link='<...>', component='<...>', story_points=<...>); print(i.key)"
   ```
   For anything multi-line or quote-heavy (usually the description), write a small temp script under `$env:TEMP` instead of inlining.
7. **Confirm back** to the user with the created issue key and a link (`<JIRA_URL>/browse/<KEY>`, `JIRA_URL` from [jira_client.py](../../../test%201/jira_client.py)).

## Notes
- Never invent or silently correct parsed field values — if something looks wrong, surface it in step 4 and let the user decide, don't fix it silently.
- Do not touch `jira_client.py`, `story_parser.py`, or `coord_finder.py` — only call their existing functions.
- `glossary.py` and `epic_aliases.py` are the exceptions: their `apply_glossary`/`resolve_epic_alias` functions are off-limits like the others, but the `GLOSSARY` dict in glossary.py and the `EPIC_ALIASES` dict in epic_aliases.py are meant to be edited directly — the former for new English→German word pairs, the latter for new epic name→key pairs.
- `capitalization.py` has no editable data (no dict) — it's off-limits like `story_parser.py`, only call `capitalize_paragraphs`.
- This skill is the create-side counterpart to `/draft` (updates an existing issue's description) and `/comment` (adds a comment) — together they cover the JIRA write paths.
