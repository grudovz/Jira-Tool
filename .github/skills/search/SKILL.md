---
name: search
description: 'Search for JIRA issues by keyword, assignee, status, and/or sprint, and display matches grouped by status via jira_client.py. Use when the user asks to "fetch"/"list"/"show" multiple issues (e.g. "issues in the current sprint that are on staging", "bugs assigned to X"), or types /search — as opposed to a single known issue key, which is /fetch.'
argument-hint: '[keyword] [assignee] [status] [sprint]'
---

# Search JIRA Issues

## When to Use
- The user wants a list of issues matching some criteria (keyword, assignee, status, sprint), not a single known issue key — for a specific key, use `/fetch` instead
- Phrases like "fetch issues with status X", "show bugs assigned to Y", "list stories in the current sprint that are on staging", or `/search`

## Procedure
1. **Parse the filter criteria** present in the request — any combination of:
   - **Keyword** — free text to match against summary/description
   - **Assignee** — a name
   - **Status** — a status word/phrase
   - **Sprint scope** — e.g. "current sprint" / "active sprint"
   All are optional; use only the ones actually given.
2. **Resolve assignee** (if given) to a JIRA user, the same way `/comment` resolves `@name` mentions:
   ```python
   jira.search_users(user="<name>", includeInactive=False)
   ```
   Exactly one match → use that user's `.name` in the JQL (`assignee = "<name>"`). Zero or multiple matches → don't guess, ask which user was meant.
3. **Resolve status** (if given) to the raw JIRA status name using the mapping table in [copilot-instructions.md](../../copilot-instructions.md) — this is the reverse direction of what `/fetch` does (internal → JIRA, not JIRA → internal). If the given status isn't in that table, don't guess a mapping — ask.
4. **Build the JQL** and run it via the existing `search_issues` function in [jira_client.py](../../../test%201/jira_client.py) — do not modify that file:
   - Always scope to `project = TRSC` (`DEFAULT_PROJECT`) unless told otherwise
   - Keyword → `text ~ "<keyword>"`
   - Assignee → `assignee = "<resolved username>"`
   - Status → `status = "<raw JIRA status>"`
   - Sprint scope → `sprint in openSprints()`
   - Combine whichever clauses apply with `AND`
   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe -c "from jira_client import search_issues; ..."
   ```
5. **Display results grouped by status**, not as one flat list. Group headings follow the row order of the mapping table in [copilot-instructions.md](../../copilot-instructions.md) (e.g. "to do" before "blocked" before "in progress" ... "approved") — not JQL/JIRA return order; an unmapped raw status heading sorts after every mapped one. Skip any status heading with zero matches.
   - **Status heading** — the internal status name in quotes, e.g. `"in progress"` (raw JIRA name instead if unmapped), on its own line
   - **Feature sub-heading** — under each status heading, group rows by `issue.fields.customfield_10006` (Feature/Epic Link):
     - Look up the epic key in [epic_aliases.py](../../../test%201/epic_aliases.py)'s alias mapping (reverse direction — epic key → alias name) and show the alias name as the sub-heading if one exists; otherwise show the raw epic key
     - No epic link at all → sub-heading "—"
     - Sub-headings sorted ascending by epic key, with "—" (no epic link) sorted last in the group
   - Under each feature sub-heading, one row per matching issue, in this column order: **Key, Issue Type, Summary, Assignee** (Status and Feature/Epic Link are both dropped from the row — they're now headings):
     - **Key** — a hyperlink: `[<KEY>](<JIRA_URL>/browse/<KEY>)` (`JIRA_URL` from [jira_client.py](../../../test%201/jira_client.py))
     - **Issue Type** — `issue.fields.issuetype.name`
     - **Summary** — `issue.fields.summary`
     - **Assignee** — `issue.fields.assignee.displayName`, or "Unassigned"
   - **Row sort order** — primary by issue type, secondary by issue key (ascending, i.e. ticket number order):
     - Type order: **Story**, then **Bug**, then **Spike** — any other type encountered (e.g. Task, Sub-task) sorts after these three, alphabetically among themselves
   - No description/comments/other detail here — that's what `/fetch` is for on a specific key from the list
6. **Zero matches**: say so plainly, not as an error.

## Notes
- Read-only — only ever calls `search_issues` (and `search_users` for assignee resolution); never updates, comments on, or transitions any issue.
- Do not touch `jira_client.py`, `story_parser.py`, `coord_finder.py`, or `epic_aliases.py` — only read their existing functions/data.
- Companion to `/fetch` (full detail for one known key) — the intended flow is `/search` to find candidates, then `/fetch` on specific keys of interest.
