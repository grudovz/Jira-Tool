---
name: releasenotes
description: 'Recurring (~every 2 weeks) bulk task: find TRSC issues moved to status Done in a date window and set a given fixVersion on them, so they get picked up in release notes. Excludes ALP IL components by default since ALP IL is a separate product with its own release notes run; pass "ALP IL" to scope to only those components instead. Use when the user types /releasenotes or asks to "run release notes" / "tag issues for release X".'
argument-hint: '[fix version] [since <date> | <date> to <date>] [ALP IL]'
---

# Release Notes: Bulk fixVersion Tagging

## When to Use
- User types `/releasenotes` or asks to run/prepare release notes for a fix version
- Always three inputs, gathered from the request or asked for if missing:
  1. **Fix version** to apply (e.g. `Bistro Connect PRD 1.7.20`)
  2. **Date scope** — a since-date (open-ended up to now) or an explicit `<start>` to `<end>` range
  3. **Product scope** — default, or `ALP IL` (see below)

## Product scope
This project currently has one defined component group that identifies a separate product with its own release notes run:
```
ALP IL components: ALP IL - Administration, ALP IL - Operation, ALP IL - Reservation
```
- **Default scope** (no product named in the request): exclude these three components — `component not in (...)`.
- **`ALP IL` named explicitly** in the request (e.g. "release notes for ALP IL"): scope to only these three — `component in (...)`.
- If a second product group is ever introduced, add it as its own named block here (mirroring this one) rather than generalizing prematurely — don't restructure this into a generic map until there's a second real case.

## Procedure
1. **Resolve the fix version.** Required — if not given, ask for it. Verify it exists in TRSC's version list before using it (a typo here would otherwise silently fail per-issue later):
   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe -c "from jira_client import jira; names=[v.name for v in jira.project_versions('TRSC')]; print('<FIX_VERSION>' in names, names)"
   ```
   Not found → tell the user and confirm before proceeding (don't guess a close match, don't create the version).
2. **Resolve the date scope.** Interpret dates as day-first (`DD/MM/YY` or `DD/MM/YYYY`, e.g. `13/8/26` → `2026-08-13`), matching how the user phrases them; 2-digit years are `20XX`. If a date is genuinely ambiguous, ask rather than guess.
   - Since-date only → JQL clause: `status changed to "Done" after "<since>"`
   - Explicit range → JQL clause: `status changed to "Done" after "<start>" AND status changed to "Done" before "<end>"`
3. **Resolve product scope** per the block above, producing either `component not in (...)` (default) or `component in (...)` (ALP IL named).
4. **Build and run the JQL** via the existing `search_issues` function in [jira_client.py](../../../test%201/jira_client.py) — do not modify that file. Note the fix version being applied is **not** part of this search query — it's what gets written in step 6, not a filter:
   ```powershell
   .\.venv\Scripts\python.exe -c "
   from jira_client import search_issues
   jql = 'project = TRSC AND status changed to \"Done\" after \"<since>\" AND component not in (\"ALP IL - Administration\", \"ALP IL - Operation\", \"ALP IL - Reservation\")'
   issues = search_issues(jql, max_results=200)
   for i in issues:
       comps = ', '.join(c.name for c in i.fields.components) if i.fields.components else 'none'
       fixv = ', '.join(v.name for v in i.fields.fixVersions) if i.fields.fixVersions else 'none'
       print(f'{i.key} | {i.fields.summary} | {comps} | existing fixVersions: {fixv}')
   "
   ```
5. **Zero matches** → say so plainly, stop here.
6. **Display the full matched list in chat** — Key (linked, `<JIRA_URL>/browse/<KEY>`), Summary, Component, existing fixVersion(s) — and **always wait for the user's explicit go-ahead** before writing anything to JIRA. Never apply the update in the same turn the list is first shown.
7. **On confirmation, apply the fix version to each matched issue.** Re-fetch each issue's current `fixVersions` immediately before updating (don't rely on the list from step 4/6, which may be stale) and add the target version alongside whatever is already there — never remove an existing fixVersion:
   ```powershell
   .\.venv\Scripts\python.exe -c "
   from jira_client import jira, update_issue
   target = '<FIX_VERSION>'
   for key in [<KEYS>]:
       try:
           issue = jira.issue(key)
           existing = [v.name for v in issue.fields.fixVersions]
           if target in existing:
               print(f'{key}: already has {target}, skipping'); continue
           new_versions = existing + [target]
           update_issue(key, fields={'fixVersions': [{'name': n} for n in new_versions]})
           print(f'{key}: OK -> {new_versions}')
       except Exception as e:
           print(f'{key}: FAILED -> {e}')
   "
   ```
   **Must pass `fields={'fixVersions': [...]}`, not a bare `fixVersions=[...]` kwarg.** `update_issue`'s `**fields` forwards straight to `Issue.update()`, whose heuristics merge list-valued kwargs into the JIRA "update operations" section (expecting `set`/`add`/`remove` keys) instead of the plain "fields" section — a bare `fixVersions=[...]` list fails with a 400 (`does not support operation 'name'`). Wrapping it in `fields={...}` routes it through the fields section correctly, which is what a plain "set this field's value" update needs.
8. **Report back**: which issues were updated (with their new fixVersion list), which were already tagged and skipped, and any that failed (with the JIRA error).

## Notes
- Read step (`search_issues`) is read-only; the write step touches only `fixVersions` via `update_issue`/`jira.issue` — do not touch `jira_client.py`, `story_parser.py`, or `coord_finder.py`, only call their existing functions.
- No auto-apply mode — this always pauses for confirmation before writing, since it's a bulk change to shared JIRA state run on a recurring cadence. If that changes later, add an explicit toggle (mirroring `/create`'s `AUTO_CREATE`) rather than silently skipping confirmation.
- Companion to `/search` (read-only lookup) — this skill is the bulk-write counterpart, scoped specifically to the recurring release-notes fixVersion tagging workflow rather than general-purpose bulk edits.
