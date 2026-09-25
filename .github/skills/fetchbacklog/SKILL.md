---
name: fetchbacklog
description: 'Fetch every TRSC backlog item (sprint is EMPTY, or in the ALP IL backlog sprint, and not Done) created since the last time this skill was run, and display each in full /fetch-style detail (condensed metadata line, description, comments, attachments) via jira_client.py. No ALP IL exclusion. Tracks "last run" via a local timestamp file, auto-updated after each run. Use when the user asks what is new in the backlog since last check, or types /fetchbacklog or says "fetch backlog".'
---

# Fetch New Backlog Items (Since Last Run)

## When to Use
- The user wants to see backlog items that are new since the last time this skill was invoked — e.g. items external colleagues have added to the backlog that may need adjustment
- Phrases like "fetch backlog", "what's new in the backlog", "any new backlog items", or `/fetchbacklog`
- Not a single known key (`/fetch`), not the active-sprint staging list (`/fetchstaging`), not a generic filtered search (`/search`)

## State file
`test 1/fetchbacklog_state.json` — holds the timestamp of the last successful run:
```json
{"last_run": "2026/09/23 14:30"}
```
- Missing file (first-ever run) → treat as "no prior run": fetch the entire current backlog, no time filter.
- After a successful fetch (even zero matches), overwrite this file with the current time, so the next run starts from here.

## Procedure
1. **Read the state file and build the JQL**, then run it via the existing `search_issues` function in [jira_client.py](../../../test%201/jira_client.py) — do not modify that file:
   ```
   project = TRSC AND (sprint is EMPTY OR sprint = 73312) AND statusCategory != Done AND created >= "<last_run>" ORDER BY created ASC
   ```
   (omit the `AND created >= "..."` clause entirely if the state file doesn't exist yet)
   `sprint = 73312` is the "ALP IL backlog" sprint — ALP IL tickets are filed directly into this standing sprint instead of the empty backlog, so it must be included alongside `sprint is EMPTY` to catch new ALP IL items.
   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe -c "
   import json, os
   from datetime import datetime
   from jira_client import search_issues

   state_path = 'fetchbacklog_state.json'
   last_run = None
   if os.path.exists(state_path):
       with open(state_path) as f:
           last_run = json.load(f).get('last_run')

   jql = 'project = TRSC AND (sprint is EMPTY OR sprint = 73312) AND statusCategory != Done'
   if last_run:
       jql += f' AND created >= \"{last_run}\"'
   jql += ' ORDER BY created ASC'

   issues = search_issues(jql, max_results=200)
   for i in issues:
       print(i.key)

   with open(state_path, 'w') as f:
       json.dump({'last_run': datetime.now().strftime('%Y/%m/%d %H:%M')}, f)
   "
   ```
   `search_issues` fetches full fields by default (no `fields=` restriction), so `description`, `comment`, and `attachment` are already present on each result — no per-issue re-fetch needed.
2. **Zero matches** → say so plainly (e.g. "No new backlog items since the last check"), not as an error. Still update the state file.
3. **Display each matched issue**, one after another, in the exact same structure and empty-field rules as `/fetch`:
   - **Key, Summary** — Key as a hyperlink (`[<KEY>](<JIRA_URL>/browse/<KEY>)`, `JIRA_URL` from [jira_client.py](../../../test%201/jira_client.py)), then `issue.fields.summary` (always shown)
   - **Condensed metadata line** — `<Issue Type> | <Status> | <Assignee> | <Epic Link> | <Component>`, values only, pipe-separated, same field sources as `/fetch`
   - **Description** — `issue.fields.description`, in full, only if set
   - **Comments** — `issue.fields.comment.comments`, each as author + body, reverse chronological order (newest first), only if any
   - **Attachments** — filenames from `issue.fields.attachment`, only if any
   - Omit empty fields/segments/sections entirely — no placeholder text, same rule as `/fetch`
   - Description and comment bodies are JIRA wiki markup, not Markdown — convert each through `jira_markup.to_markdown()` (see [jira_markup.py](../../../test%201/jira_markup.py)) before displaying, and render the result as real Markdown (bold, bullet lists, links) directly in the chat response. Never show the raw JIRA markup literally and never wrap it in a code fence.

## Notes
- Read-only against JIRA — only ever calls `search_issues`; never updates, comments on, or transitions any issue. The only side effect is overwriting the local state file.
- Do not touch `jira_client.py`, `story_parser.py`, or `coord_finder.py` — only call the existing function.
- No ALP IL exclusion (unlike `/fetchstaging`/`/releasenotes`) — backlog triage covers everything, and `sprint = 73312` ("ALP IL backlog") is explicitly included so ALP IL items filed directly into that standing sprint aren't missed.
- `fetchbacklog_state.json` is gitignored — it's local run state, not project config.
