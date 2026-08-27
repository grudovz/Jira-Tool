---
name: fetchstaging
description: 'Fetch every TRSC issue on staging (status "In Test") in the current/active sprint, and display each in full /fetch-style detail (condensed metadata line, description, comments, attachments) via jira_client.py. Excludes ALP IL components by default since ALP IL is a separate product with its own release notes run; pass "ALP IL" to scope to only those components instead. Use when the user asks to fetch/list/show what is on staging right now to test, or types /fetchstaging or says "fetch staging".'
argument-hint: '[ALP IL]'
---

# Fetch Staging Issues (Current Sprint)

## When to Use
- The user wants full detail on every issue currently on staging in the active sprint, to test — not a single known key (`/fetch`) and not a generic filtered compact list (`/search`)
- Phrases like "fetch staging", "what's on staging right now", "show me everything to test in the current sprint", or `/fetchstaging`
- `"fetch staging ALP IL"` scopes to ALP IL components only (see Product scope below); otherwise ALP IL is excluded

## Product scope
Same ALP IL component group as `/releasenotes` — keep these two definitions in sync if the list ever changes:
```
ALP IL components: ALP IL - Administration, ALP IL - Operation, ALP IL - Reservation
```
- **Default scope** (no product named in the request): exclude these three components — `component not in (...)`.
- **`ALP IL` named explicitly** in the request: scope to only these three — `component in (...)`.

## Procedure
1. **Build the JQL** and run it via the existing `search_issues` function in [jira_client.py](../../../test%201/jira_client.py) — do not modify that file:
   ```
   project = TRSC AND status = "In Test" AND sprint in openSprints() AND component not in ("ALP IL - Administration", "ALP IL - Operation", "ALP IL - Reservation")
   ```
   (swap the `component` clause to `in (...)` when ALP IL scope was requested)
   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe -c "from jira_client import search_issues; issues = search_issues('<JQL>', max_results=200); ..."
   ```
   `search_issues` fetches full fields by default (no `fields=` restriction), so `description`, `comment`, and `attachment` are already present on each result — no per-issue re-fetch needed.
2. **Zero matches** → say so plainly, not as an error.
3. **Display each matched issue**, one after another, in the exact same structure and empty-field rules as `/fetch`:
   - **Key, Summary** — `issue.key`, `issue.fields.summary` (always shown)
   - **Condensed metadata line** — `<Issue Type> | <Status> | <Assignee> | <Epic Link> | <Component>`, values only, pipe-separated, same field sources as `/fetch` (Status will always read "on staging" here, since that's the filter)
   - **Description** — `issue.fields.description`, in full, only if set
   - **Comments** — `issue.fields.comment.comments`, each as author + body, reverse chronological order (newest first), only if any
   - **Attachments** — filenames from `issue.fields.attachment`, only if any
   - Omit empty fields/segments/sections entirely — no placeholder text, same rule as `/fetch`

## Notes
- Read-only — only ever calls `search_issues`; never updates, comments on, or transitions any issue.
- Do not touch `jira_client.py`, `story_parser.py`, or `coord_finder.py` — only call the existing function.
- Companion to `/search` (generic filtered compact list) and `/fetch` (single known key, full detail) — this skill is the fixed-filter, full-detail, multi-issue combination of the two, purpose-built for "what do I need to test right now."
