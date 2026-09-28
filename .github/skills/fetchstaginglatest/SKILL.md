---
name: fetchstaginglatest
description: 'Manually-triggered digest of two things since this skill was last run: (1) TRSC comments mentioning the user (literal "[~zgrudov]" mention syntax), and (2) TRSC issues that moved to "In Test" (staging). First-ever run looks back 24 hours instead of full history. Tracks "last run" via a local timestamp file, auto-updated after each run. Use when the user asks "fetch staging latest", "did anyone mention me", or types /fetchstaginglatest. Not on a schedule — manual only.'
---

# Fetch Staging Latest (Mentions + New Staging Items, Since Last Run)

## When to Use
- The user wants a manual check-in covering both new mentions of them and new items moved to staging, since the last time this skill was invoked
- Phrases like "fetch staging latest", "fetch mentions", "did anyone mention me", "any new mentions", or `/fetchstaginglatest`
- Manual only — this is not on a recurring schedule (unlike `/fetchbacklog`); run it only when the user explicitly asks
- Not a single known key (`/fetch`), not the full current-sprint staging list (`/fetchstaging`), not the backlog digest (`/fetchbacklog`), not a generic filtered search (`/search`)

## State file
`test 1/fetchstaginglatest_state.json` — holds the timestamp of the last successful run:
```json
{"last_run": "2026/09/28 10:33"}
```
- Missing file (first-ever run) → treat as "no prior run": use a 24-hour lookback instead of full history (bootstrap window — avoids flooding with old mentions/staging moves).
- After a successful run (even zero matches on both fronts), overwrite this file with the current time, so the next run starts from here.

## Procedure
1. **Read the state file and compute the since-timestamp** (either the stored `last_run`, or 24 hours ago on first run), then run **two independent queries** via the existing `search_issues` function in [jira_client.py](../../../test%201/jira_client.py) — do not modify that file:

   **(a) Mentions** — JQL text search is only an inclusive shortlist; the precise `[~zgrudov]` match happens in Python afterward:
   ```
   project = TRSC AND comment ~ "zgrudov" AND updated >= "<since>"
   ```
   Filter results to comments where the literal substring `[~zgrudov]` appears in `comment.body` **and** `comment.created` (parsed via `dateutil.parser.parse`, converted to naive local time) is strictly after the since-timestamp.

   **(b) Moved to staging** — issues that transitioned into "In Test" since the since-timestamp (same clause style as `/releasenotes`'s `status changed to "Done" after "..."`, just a different status):
   ```
   project = TRSC AND status changed to "In Test" after "<since>"
   ```
   No further Python-side filtering needed — the JQL clause itself is precise (unlike free-text comment search).

   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe -c "
   import json, os
   from datetime import datetime, timedelta
   from dateutil import parser as dtparser
   from jira_client import search_issues, JIRA_URL

   state_path = 'fetchstaginglatest_state.json'
   last_run = None
   if os.path.exists(state_path):
       with open(state_path) as f:
           last_run = json.load(f).get('last_run')

   if last_run:
       since_dt = datetime.strptime(last_run, '%Y/%m/%d %H:%M')
   else:
       since_dt = datetime.now() - timedelta(hours=24)
   since_str = since_dt.strftime('%Y/%m/%d %H:%M')

   mention_issues = search_issues(f'project = TRSC AND comment ~ \"zgrudov\" AND updated >= \"{since_str}\"', max_results=200)
   mentions = []
   for issue in mention_issues:
       matches = [
           c for c in issue.fields.comment.comments
           if '[~zgrudov]' in c.body
           and dtparser.parse(c.created).astimezone().replace(tzinfo=None) > since_dt
       ]
       if matches:
           mentions.append((issue, matches))

   staged_issues = search_issues(f'project = TRSC AND status changed to \"In Test\" after \"{since_str}\"', max_results=200)

   for issue, matches in mentions:
       print('MENTION', issue.key, issue.fields.summary, len(matches))
   for issue in staged_issues:
       print('STAGED', issue.key, issue.fields.summary)

   with open(state_path, 'w') as f:
       json.dump({'last_run': datetime.now().strftime('%Y/%m/%d %H:%M')}, f)
   "
   ```
   `search_issues` fetches full fields by default, so `issue.fields.comment.comments` is already present on each result — no per-issue re-fetch needed.
2. **Zero matches on both fronts** → say so plainly (e.g. "No new mentions or staging moves since the last check"), not as an error. Still update the state file. If only one front has matches, report that one and say the other is empty.
3. **Display results in two sections**, each digest-style (not full `/fetch`-style detail):
   - **New mentions**: per issue — Key as a hyperlink (`[<KEY>](<JIRA_URL>/browse/<KEY>)`, `JIRA_URL` from [jira_client.py](../../../test%201/jira_client.py)), summary, then for each matching comment: author display name, timestamp, and the comment body (through `jira_markup.to_markdown()`, rendered as real Markdown, never raw/code-fenced)
   - **Moved to staging**: per issue — Key (linked), summary, and its current status (an issue can have moved to "In Test" and since progressed further, e.g. to "Done" — still worth surfacing as "moved to staging" since the last check, so show its current status alongside)
   - An issue appearing in both sections (mentioned *and* moved to staging) is fine — no dedup needed, just show it in both
   - No attachment caching here — out of scope for a digest

## Notes
- Read-only against JIRA — only ever calls `search_issues`; never updates, comments on, or transitions any issue. Overwriting the local state file is the only side effect.
- Do not touch `jira_client.py`, `story_parser.py`, or `coord_finder.py` — only call the existing function.
- Scoped to TRSC only; mentions are comments-only (not descriptions) — matches this tool's existing scope and how mentions are actually written in this project (see `/comment`'s mention-resolution logic).
- `fetchstaginglatest_state.json` is gitignored — it's local run state, not project config.
- Manual only, no cron job — unlike `/fetchbacklog`, don't schedule this unless the user explicitly asks again.
