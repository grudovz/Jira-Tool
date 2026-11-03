---
name: exportsprintreview
description: 'Export every TRSC issue moved to status Done within a two-week sprint window to a CSV (Key, Summary, Assignee, Component, Issue Type, Epic, Description), for handing off to another agent that builds a sprint review PowerPoint. The window defaults to the current two-week cadence computed from a fixed anchor (2026-10-12 to 2026-10-23), or an explicit date range can be given instead. Includes ALP IL by default (same team). Use when the user asks to export sprint review issues, or types /exportsprintreview.'
argument-hint: '[<date> to <date>]'
---

# Export Sprint Review Issues

## When to Use
- The user asks to export completed/Done issues for a sprint review presentation, or types `/exportsprintreview`
- Produces a CSV handoff file for a different agent to build a PowerPoint from — this skill never builds the presentation itself
- Not a general completed-issues search (that's `/search`) and not the release-notes fixVersion tagging workflow (`/releasenotes`) — this is read-only and scoped specifically to the recurring sprint-review export

## Window resolution
Two-week sprint cadence, anchored at **2026-10-12 (Mon)** — the first test window runs **2026-10-12 to 2026-10-23 (Fri)**, confirmed against this project's actual sprint boundaries (also Fridays, 14/28 days apart).
- **No dates given** → auto-compute the window containing today:
  ```python
  from datetime import date, timedelta
  ANCHOR = date(2026, 10, 12)
  today = date.today()
  n = (today - ANCHOR).days // 14
  start = ANCHOR + timedelta(days=14 * n)
  end = start + timedelta(days=11)
  ```
  This always resolves to the Mon–Fri window today falls in (an intervening weekend still belongs to the window that just ended, since the `// 14` step doesn't advance until the next Monday).
- **Explicit range given** → interpret dates as day-first (`DD/MM/YY` or `DD/MM/YYYY`, e.g. `13/8/26` → `2026-08-13`), matching `/releasenotes`'s date convention; 2-digit years are `20XX`. Ambiguous date → ask rather than guess.

## Procedure
1. **Resolve the date window** per the rules above.
2. **Build and run the JQL** via the existing `search_issues` function in [jira_client.py](../../../test%201/jira_client.py) — do not modify that file. No ALP IL exclusion (unlike `/releasenotes`/`/fetchstaging`) — ALP IL is the same team, and a sprint review should cover all of the team's completed work.

   The `before` clause uses `end + 1 day`, not the raw end date — JIRA's bare-date `before "X"` excludes the entirety of day X, while `after "X"` is effectively inclusive of day X. Without this adjustment, anything moved to Done on the window's last day (often the busiest) would be silently dropped.
   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe -c "
   from datetime import date, timedelta
   from jira_client import search_issues
   from jira_markup import to_markdown
   import csv

   start = date(<start_year>, <start_month>, <start_day>)
   end = date(<end_year>, <end_month>, <end_day>)
   end_excl = end + timedelta(days=1)

   jql = f'project = TRSC AND status changed to \"Done\" after \"{start}\" AND status changed to \"Done\" before \"{end_excl}\" ORDER BY key ASC'
   issues = search_issues(jql, max_results=200)

   if not issues:
       print('NO_MATCHES')
   else:
       path = f'drafts/sprint_review_{start}_{end}.csv'
       with open(path, 'w', newline='', encoding='utf-8') as f:
           writer = csv.writer(f)
           writer.writerow(['Key', 'Summary', 'Assignee', 'Component', 'Issue Type', 'Epic', 'Description'])
           for i in issues:
               assignee = i.fields.assignee.displayName if i.fields.assignee else ''
               components = ', '.join(c.name for c in i.fields.components) if i.fields.components else ''
               issue_type = i.fields.issuetype.name
               epic = getattr(i.fields, 'customfield_10006', None) or ''
               description = to_markdown(i.fields.description) if i.fields.description else ''
               writer.writerow([i.key, i.fields.summary, assignee, components, issue_type, epic, description])
       print(f'WROTE {len(issues)} {path}')
   "
   ```
3. **Zero matches** (`NO_MATCHES`) → report plainly in chat (e.g. "No issues moved to Done between `<start>` and `<end>`"), stop here — don't create a CSV file.
4. **On success**, report in chat:
   - The resolved date window
   - A compact table of what was exported — **Key | Summary | Assignee | Component | Issue Type | Epic** (no Description column — too long for chat; it's in the CSV for the downstream agent)
   - The row count and the output file path (`test 1/drafts/sprint_review_<start>_<end>.csv`)

## Notes
- Read-only against JIRA — only ever calls `search_issues`; never updates, comments on, or transitions any issue. Writing the local CSV file is the only side effect.
- Do not touch `jira_client.py`, `story_parser.py`, or `coord_finder.py` — only call the existing `search_issues` function. `jira_markup.py` is used read-only via `to_markdown`.
- Output CSV is plain UTF-8, no BOM, written with Python's stdlib `csv` module (there's no reusable CSV-writing helper in this repo — every prior export, including this one, is inline Python matching `/releasenotes`'s and `/fetchbacklog`'s house style).
- Epic is read from `customfield_10006` (the classic "Epic Link" field — a plain epic key string like `LPDA-1777`, or empty if the issue isn't linked to an epic). Same field `create_issue` writes to in `jira_client.py`, and the same mechanism `epic_aliases.py` resolves dictated aliases into.
- The `end + 1 day` adjustment to the JQL `before` clause is deliberate and differs from `/releasenotes`, which doesn't apply it — don't "fix" this skill to match that one, or vice versa, without re-checking which is actually correct for that skill's own use case.
- The 2026-10-12 anchor is fixed in this file. If the sprint cadence ever shifts (a window added/skipped, start day changes), update `ANCHOR` here rather than trying to infer it from JIRA at runtime.
