# Copilot Instructions — JIRA Story Tool

## Project purpose
An internal tool for creating, updating, commenting on, and analysing JIRA issues. Used by a single developer/BA with Dragon NaturallySpeaking voice input.

## Primary workflow (current)
Day-to-day work happens directly in VS Code Copilot Chat, which calls `jira_client.py` (and `story_parser.py` when parsing pasted text) via terminal one-liners or small temp scripts — no UI required. Reusable steps are packaged as agent skills:
- `/comment` — [.github/skills/comment/SKILL.md](../.github/skills/comment/SKILL.md) — add a comment to a JIRA issue
- `/analyse` — [.github/skills/analyse/SKILL.md](../.github/skills/analyse/SKILL.md) — analyse a draft story or business/technical requirements pasted into the session, grounded in the actual client/server code and UI screenshots; output stays in chat for iterative back-and-forth
- `/draft` — [.github/skills/draft/SKILL.md](../.github/skills/draft/SKILL.md) — write the current best version of a story (latest analysis, latest input, or explicit instructions) to the scratch file `test 1/drafts/item.md` (dictation-friendly, since it's a real editor document); does not touch JIRA
- `/create` — [.github/skills/create/SKILL.md](../.github/skills/create/SKILL.md) — parse pasted issue text via `story_parser.py` and create a new JIRA issue via `jira_client.py`; asks for confirmation after parsing until the `AUTO_CREATE` flag in that file is flipped on
- `/fetch` — [.github/skills/fetch/SKILL.md](../.github/skills/fetch/SKILL.md) — fetch and display a single JIRA issue's details by key (status shown as its internal mapped status only)
- `/search` — [.github/skills/search/SKILL.md](../.github/skills/search/SKILL.md) — search issues by keyword/assignee/status/sprint and display a compact list (Key, Summary, Component, Status, Assignee); use `/fetch` on a specific key from the results for full detail
- `/fetchstaging` — [.github/skills/fetchstaging/SKILL.md](../.github/skills/fetchstaging/SKILL.md) — fetch every issue on staging in the current sprint and display each in full `/fetch`-style detail (description, comments, attachments); excludes ALP IL components by default, same as `/releasenotes`
- `/releasenotes` — [.github/skills/releasenotes/SKILL.md](../.github/skills/releasenotes/SKILL.md) — recurring (~every 2 weeks) bulk task: find TRSC issues moved to Done in a date window, excluding ALP IL components by default (separate product, own release notes run), and set a given fixVersion on them; always confirms the matched list before writing

For code-grounded analysis, open [jira-story-tool.code-workspace](../jira-story-tool.code-workspace) (multi-root: this folder + `trsc-client` + `trsc-gateway`) instead of just this folder.

The Streamlit UI (`app.py`) is **on hold**. Do not propose changes, fixes, or improvements to it, and do not factor it into suggestions for other files, unless the user explicitly asks for UI work. It is left as-is and is not a target for future iteration.

## Attachment handling
Applies whenever a message that posts a JIRA comment or updates an issue's description/fields — via `/comment`, or an ad-hoc "add a comment"/"update this issue" request typed directly in chat — includes one or more pasted images.
- Attach each pasted image to that same issue automatically via `attach_file` in [jira_client.py](../test%201/jira_client.py) — standing approval, no need to ask each time (same pattern as `/comment`'s `@mention` resolution and Done-transition check).
- Pass the image's file path directly to `attach_file(issue_key, path)` — no need to copy, re-encode, or rename it first.
- More than one image on the same message → attach all of them.
- Only applies to comment/update actions. `/create` already has its own explicit `attachments` parameter for issue creation, and `/draft` never touches JIRA — neither needs this rule.
- No pasted image on the triggering message → nothing to do here, don't mention it.

## Folder layout
```
test 1/
  jira_client.py      — JIRA API wrapper, do not refactor without asking.
  story_parser.py     — Rule-based text parser. No LLM dependency. Pure functions only.
  bug_parser.py       — Rule-based parser/formatter for bug report descriptions. No LLM dependency. Pure functions only.
  app.py              — Streamlit UI. On hold, do not modify/suggest changes unless explicitly asked — see Primary workflow above.
  drafts/             — Gitignored scratch folder for the /draft skill; item.md holds the current draft for review/dictation.
  analysis-context/   — Gitignored screenshots (current + reference) supplied as context for the /analyse skill.
  tests/
    test_parser.py      — Unit tests for story_parser.py
    test_bug_parser.py  — Unit tests for bug_parser.py
  main.py             — Legacy CLI entry point. Kept for reference.
  requirements.txt    — Pinned dependencies.
```

## Architecture rules
- `app.py` must never call the JIRA API directly — always via `jira_client.py`
- Skills are mirrored in two locations — `.github/skills/<name>/SKILL.md` (Copilot) and `.claude/skills/<name>/SKILL.md` (Claude Code) — and must stay byte-identical. Whenever a skill is created or edited in one location, apply the exact same change to the other in the same commit.
- `story_parser.py` must remain free of network calls and external dependencies
- `bug_parser.py` must remain free of network calls and external dependencies

## Related projects
`../ui-macros/` (sibling folder, not part of this workspace root) is a separate Windows desktop-automation project — unrelated codebase and purpose. It used to keep a mouse-coordinate probe (`coord_finder.py`) here during early exploration; that file and the `pyautogui`/`keyboard`/`pygetwindow`/`opencv-python`/`Pillow` dependencies it needed have moved there. Don't factor that project's concerns into this one.

## Story parsing rules (`story_parser.py`)
`parse_issue(raw_text)` is a pure regex parser (no LLM, no network) for pasted issue text in a fixed, dictation-friendly layout:
```
<summary>
issue: <value>       (optional)
epic: <value>        (optional, "feature:" also accepted as an alias)
component: <value>   (optional)
points: <value>      (optional)
<description — everything else>
```
Rules:
1. **Line 1 is always the summary** — whatever's on the first non-empty line, no matter its content. Blank → `summary` is `None`.
2. **Field lines must come immediately after the summary**, each its own line as `label: value` (case-insensitive, flexible spacing — `Issue:`, `issue :`, `ISSUE:` all match). Recognized labels: `issue`, `epic`/`feature`, `component`, `points`/`point` (short, voice-dictation-friendly forms — the parsed dict keys are still `issue_type`/`epic_link`/`story_points` internally, only the input label text changed). `feature` is scoped to the field-line position only (start of line, immediately followed by `:`) — it does not affect the word "feature" appearing elsewhere in the summary/description.
3. **Blank lines between the summary and field lines are skipped** and don't end the field block.
4. **The first line that isn't a recognized field line ends the field block** — everything from there to the end of the text becomes `description`, verbatim. A field-like line appearing later, inside the description, is not parsed as a field — it's just description text.
5. **Points** extracts the first run of digits found in that line's value (e.g. `points: ~3 or so` → `3`); no digits found → stays `None`.
6. **Anything not found is `None`** — the parser never invents or defaults a value. Defaulting (issue type → "Story", epic link → `DEFAULT_EPIC_LINK`, component → `DEFAULT_COMPONENT`) is `jira_client.create_issue`'s job, and only kicks in when the field is *omitted* from the call — not when it's an empty string. This is why `/create` explicitly omits any `None` field rather than passing it through.

## Story Writing Conventions
Team conventions for what a well-formed story should contain, beyond what `story_parser.py`/JIRA structurally require. Both `/analyse` (checks input against these) and `/draft` (applies them when assembling content) reference this same list — it's the single source of truth for both skills; add new conventions here rather than duplicating them into either skill file.

### Description structure
The description is generally split into these sections, in this order. **Background and Technical Details are optional; Acceptance Criteria is expected:**
- **Background** *(optional)* — high-level business requirements, if necessary. The traditional agile format ("As a user, I want X, so that Y"), when available, belongs here as part of Background rather than as its own section.
- **Technical Details** *(optional)* — where to fetch data, data mapping to UI elements, requests to external systems (e.g. NLT), and similar implementation details. Present data mappings in JSON-like format.
- **Acceptance Criteria** — the acceptance criteria, inclusive of UI changes (see conventions below).

Leave an additional blank line between each section — not just between a heading and its content, but between one section's content and the next section's heading.

Section headings (`Background`, `Technical Details`, `Acceptance Criteria`, and the Acceptance Criteria sub-headings below) are written wrapped in JIRA's bold wiki markup — single asterisks, e.g. `*Background*` — not plain text, so they render bold in JIRA without a separate formatting step later. Applies wherever this content is assembled: `/draft`'s scratch file and any description text headed to `/create`/`update_issue`.

### Acceptance criteria conventions
- **Included in the description** — not left as a separate field or omitted.
- **Split by kind, each in its own sub-section** — Functional Requirements, Error Handling, and Technical Requirements (only the sub-sections that actually apply) should each be broken out separately within Acceptance Criteria, rather than combined into a single criterion per UI element.
- **One requirement per bullet point/sentence** — each distinct requirement within a sub-section gets its own bullet (not numbered) or sentence; never combine more than one requirement into the same line.
- **Language should be simple and direct.**

### Terminology
Known application/system names, so they aren't mistaken for typos or dictation duplication during analysis:
- **Bistro Connect** — one of the applications this team supports.

### Notification types
The application has four notification types: **success**, **info**, **warning**, **error**. When a story specifies feedback shown to the user (e.g. on save, on send success/failure), reference one of these rather than inventing different notification vocabulary — and check the "Feedback provided to the user" point of the Completeness lens below against this list.

### Bug Report Description Format (`bug_parser.py`)
`/create` uses this whenever the parsed `issue_type` is `Bug`. The raw description (everything `story_parser.parse_issue` returns as `description`) is expected in this dictation-friendly shape:
```
Steps
<step 1>
<step 2>
...
<blank line>
<expected result — everything after the blank line>
```
`bug_parser.parse_bug_description` transforms that into the final JIRA-formatted description:
```
Tested in version: 1.8.0

*Steps*

1) <step 1>
2) <step 2>

*Expected result:*

<expected result>
```
- `1.8.0` comes from `DEFAULT_APP_VERSION` in `bug_parser.py` — the single source of truth for the current application version. Update it there when the user gives a new one; don't hardcode the version anywhere else.
- If the raw description doesn't match the expected `Steps`/blank-line/expected-result shape, `parse_bug_description` returns `None` and `/create` leaves the description untouched, flagging this to the user rather than guessing.

### Completeness lens (used by `/analyse`)
When analysing a story or requirements, consider whether the following have been addressed:
- User flow, including error handling and edge cases
- Discoverability of the feature
- Feedback provided to the user, where applicable
- Data flow / data availability considerations — including what should happen when new data fields being introduced are partially or fully missing/null (e.g. hide the whole section, show partial data, fall back to something else?). Stories that introduce a new data-driven section/field often only describe the happy path and skip this — treat it as a gap to flag, not an edge case to skip.
- Potential component state issues
- Potential security issues arising from the requirements

### Code-grounding scope (used by `/analyse` and `/draft`)
When the client/gateway code is available (multi-root workspace open), use it only to:
- Verify whether the business/functional requirements as written are technically feasible against the current architecture/data model.
- Surface a technical limitation or dependency relevant to the story that the story doesn't already address (e.g. upstream data not yet available from an external system).

Never use code to produce implementation-level recommendations — which files, functions, classes, or migrations to change. Figuring that out is the developers' job at implementation time, not something the story or its analysis should prescribe. If the code confirms a requirement is already fully supported, no code-level detail needs to be surfaced at all.

Notes:
- When the user mentions a new convention, add it here as a bullet in the relevant subsection.
- `/analyse` flags gaps against this list in its feedback — except missing optional sections (Background, Technical Details), which are never flagged since they're optional by design. `/draft` applies this list when assembling content but never invents details to satisfy it — a gap that can't be filled from the actual source should surface as feedback, not fabricated text.

## JIRA status mapping (internal enum)
This project's JIRA workflow statuses map to an internal status vocabulary the user thinks/talks in. Use this table whenever the user refers to an item by its internal status (e.g. "move this to on staging", "what's blocked right now"), and when reporting statuses back — translate JIRA's raw status name to the internal one so it matches how the user actually refers to it.

| JIRA status | Internal status |
|---|---|
| To Do | to do |
| New | blocked |
| In Progress | in progress |
| In Review | code review |
| To Refine | on dev |
| In Test | on staging |
| Verify | test failed |
| Done | approved |

This table's row order is also the canonical status order — whenever a skill displays multiple issues, arrange them by this sequence (not JQL/JIRA return order).

Notes:
- This is specific to the `TRSC` project's workflow as configured today — if a differently-configured JIRA project is ever used with this tool, re-confirm the mapping rather than assuming it carries over.
- If a status is encountered that isn't in this table, ask the user what it should map to and add it here — don't guess or invent a mapping.
- **Where this applies**: only to `transition_issue(issue_key, transition_name)` in [jira_client.py](../test%201/jira_client.py) — confirmed that every transition's action name matches its destination status name exactly (e.g. the transition named `'To Refine'` moves the issue to status `'To Refine'`), so translate the internal name to its JIRA name from this table and pass that straight through as `transition_name`.
  - `create_issue` has no `status` parameter by design — JIRA assigns the initial status from the project's workflow scheme; it can't be set at creation time.
  - `update_issue`'s `**fields` catch-all would technically accept a `status=` kwarg, but it would fail — JIRA doesn't support status changes via the field-update endpoint, only via workflow transitions. Never pass `status` to `update_issue`; use `transition_issue` instead.

## Dragon NaturallySpeaking compatibility
Applies to the chat+skills workflow (draft files, comments) and only to `app.py` if UI work is explicitly requested:
- All text inputs must be standard HTML inputs or textareas (Streamlit default — do not use custom JS widgets)
- Button labels must be short, unique, and pronounceable (e.g. "Parse", "Create", "Update")
- Avoid sliders, drag interactions, or non-standard controls

## Testing conventions
- Use `pytest`
- Unit test `story_parser.py` exhaustively — it is pure Python with no mocks needed
- Mock `jira_client.jira` using `unittest.mock.patch` for any test touching JIRA logic
- Do not write tests that hit the real JIRA API
- Suggest updates to the existing tests, or to write new tests whenever any updates to the code would require that.

## Planned iterations
1. **Done** — Basic Streamlit UI: paste text, parse fields, create/update issues in JIRA
2. **Done** — Chat + skills workflow (`/comment`, `/draft`) now the primary way of working; superseded the need to actively develop the UI further for now
3. **Done** — AI analysis of story quality now happens via the `/analyse` skill (the chat agent itself), grounded in real code and screenshots; the old in-app `ai_client.py` integration (Azure OpenAI/Ollama) was removed as redundant — see Architecture rules
4. **On hold, not a target for suggestions** — `app.py` itself: leave as-is unless the user explicitly requests UI work
4. **Later** — Code repository context for analysis (file tree + relevant file injection)
5. **Done** — search/filter existing issues (`/search`) and recurring bulk fixVersion tagging for release notes (`/releasenotes`)
6. **Later** — Delete issue, other bulk operations beyond fixVersion tagging

## Environment variables (.env)
```
JIRA_URL=
JIRA_USER=
JIRA_API_TOKEN=
```
