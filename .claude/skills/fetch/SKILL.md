---
name: fetch
description: 'Fetch and display the details of a single JIRA issue by key via jira_client.py. Use when the user asks to "fetch"/"retrieve"/"get" details for an issue, or types /fetch, giving a full key or shorthand digits. Also triggers on a bare issue key/number with no other wording at all (e.g. just "2942") — a deliberate shortcut for voice dictation.'
argument-hint: '[issue-key]'
---

# Fetch JIRA Issue Details

## When to Use
- The user asks to fetch/retrieve/get details for a specific issue, or types `/fetch`
- **A bare issue key or shorthand digits with nothing else** (e.g. "2942", "TRSC-2942") — treat this alone as an implicit `/fetch` request, no "fetch"/"get"/"retrieve" wording needed. This is a deliberate shortcut for dictation — saying just the number should be enough.
- A single, known issue key is given (full or shorthand) alongside other wording — for searching by keyword, assignee, or status instead of a specific key, that's a separate `/search` skill, not this one

## Procedure
1. **Resolve the issue key**: accept a full key (e.g. `TRSC-2294`) or shorthand digits (e.g. `2294`, prefixed with `DEFAULT_PROJECT` from [jira_client.py](../../../test%201/jira_client.py) to form `TRSC-2294`). Never guess — ask if no key is given.
2. **Fetch the issue** via the existing `get_issue` function in [jira_client.py](../../../test%201/jira_client.py) — do not modify that file:
   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe -c "from jira_client import get_issue; i = get_issue('<KEY>'); ..."
   ```
3. **Display in chat** (read the fields directly off the returned issue object — no invented values):
   - **Key, Summary** — Key as a hyperlink (`[<KEY>](<JIRA_URL>/browse/<KEY>)`, `JIRA_URL` from [jira_client.py](../../../test%201/jira_client.py)), then `issue.fields.summary` (always shown — never empty)
   - **Condensed metadata line** — Issue Type, Status, Assignee, Epic Link, and Component on a single line, **values only, no field labels**, pipe-separated, in this fixed order:
     `<Issue Type> | <Status> | <Assignee> | <Epic Link> | <Component>`
     - Issue Type — `issue.fields.issuetype.name` (always present)
     - Status — resolved *only* to its internal status using the mapping table in [copilot-instructions.md](../../copilot-instructions.md) (e.g. "on staging", not "In Test"); if `issue.fields.status.name` isn't in that table, show the raw JIRA status name instead and flag it as unmapped — don't guess a mapping (always present)
     - Assignee — `issue.fields.assignee.displayName`, only if set
     - Epic Link — `issue.fields.customfield_10006`, only if set
     - Component(s) — `[c.name for c in issue.fields.components]` joined by comma, only if non-empty
     - If Assignee/Epic Link/Component is empty, drop that segment from the line entirely (per the empty-field rule below) rather than leaving a blank/placeholder — since this format has no labels, a dropped segment is positionally ambiguous, but that's an accepted tradeoff for a shorter, dictation-friendly line.
   - **Description** — `issue.fields.description`, in full, only if set
   - **Comments** — `issue.fields.comment.comments`, each as author (`.author.displayName`) + body (`.body`), in reverse chronological order (newest first), only if there's at least one
   - **Attachments** — filenames from `issue.fields.attachment`, only if there's at least one
   - Description and comment bodies are JIRA wiki markup, not Markdown — convert each through `jira_markup.to_markdown()` (see [jira_markup.py](../../../test%201/jira_markup.py)) before displaying, and render the result as real Markdown (bold, bullet lists, links) directly in the chat response. Never show the raw JIRA markup literally and never wrap it in a code fence.
4. **If there are any attachments**, cache them locally and register each as a clickable link — see [Attachment caching for fetch skills](../../copilot-instructions.md#attachment-caching-for-fetch-skills).
5. **Do not show** Reporter, Priority, Created/Updated dates, or Story Points by default — only fetch and display these if the user explicitly asks for them in that request.
6. **Omit empty fields entirely** — if a field has no value (no assignee, no epic link, no components, no description, no comments, no attachments), don't include that section/line (or segment, for the condensed metadata line) in the response at all. No placeholder text ("Unassigned", "No comments", "None", etc.) — the section is simply absent for that item. This applies to every field except Key, Summary, Issue Type, and Status, which are always present on a JIRA issue and always shown.

## Notes
- Purely read-only against JIRA — only ever calls `get_issue`; never updates, comments on, or transitions the issue. Downloading attachments to the local cache is the one side effect (see step 4).
- Do not touch `jira_client.py`, `story_parser.py`, or `coord_finder.py` — only call the existing `get_issue` function. `attachment_helper.py` is fine to touch (see its own file), but keep it a thin wrapper.
- Companion to `/search` (fetching multiple issues by keyword/assignee/status — separate skill) and `/comment`/`/draft`/`/create` (the write-side skills) — together they cover reading and writing JIRA issues from chat.
