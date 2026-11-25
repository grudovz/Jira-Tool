---
name: releasenotes
description: 'Recurring (~every 2 weeks) bulk task: find TRSC issues moved to status Done in a date window and set a given fixVersion (= the JIRA release) on them, so they show up under that release; with no date scope given, the window is the release''s own start and release dates. Excludes ALP IL components by default since ALP IL is a separate product with its own release notes run; pass "ALP IL" to scope to only those components instead. As the last step marks the release as released and creates the next numbered release (e.g. "Bistro Connect release 3" -> "release 4"). Use when the user types /releasenotes or asks to "run release notes" / "tag issues for release X".'
argument-hint: '[fix version / release] [since <date> | <date> to <date>] [ALP IL]'
---

# Release Notes: Bulk fixVersion Tagging

## When to Use
- User types `/releasenotes` or asks to run/prepare release notes for a fix version
- Three inputs, gathered from the request or asked for if missing:
  1. **Fix version** to apply (e.g. `Bistro Connect release 3`). It is the same thing as the JIRA **release**: tagging issues with it is what makes them show up under that release in JIRA
  2. **Date scope** — optional. A since-date (open-ended up to now) or an explicit `<start>` to `<end>` range. **Not given → use the release's own start and release dates** (see step 2)
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
1. **Resolve the fix version and read its dates.** Required — if not given, ask for it. Verify it exists in TRSC's version list before using it (a typo here would otherwise silently fail per-issue later), and read its dates and released flag in the same call:
   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe -c "
   from jira_client import jira
   names = [v.name for v in jira.project_versions('TRSC')]
   v = next((v for v in jira.project_versions('TRSC') if v.name == '<FIX_VERSION>'), None)
   print(v is not None, names[-8:])
   if v: print(v.id, 'start:', getattr(v, 'userStartDate', None), 'release:', getattr(v, 'userReleaseDate', None), 'released:', v.released)
   "
   ```
   Not found → tell the user and confirm before proceeding (don't guess a close match, don't create the version).

   **Always read `userStartDate` / `userReleaseDate`, never `startDate` / `releaseDate`.** In this JIRA the plain fields come back one day earlier than what the Releases page shows (verified 2026-11-24 on three versions: `startDate` 2026-10-21 vs the UI's 2026-10-22). The `user…` fields are the dates the user sees and sets.
2. **Resolve the date scope.** Interpret dates as day-first (`DD/MM/YY` or `DD/MM/YYYY`, e.g. `13/8/26` → `2026-08-13`), matching how the user phrases them; 2-digit years are `20XX`. If a date is genuinely ambiguous, ask rather than guess.
   - **No date scope in the request** → use the release's own dates from step 1: `userStartDate` to `userReleaseDate`, both inclusive (explicit-range clause below). If `userReleaseDate` is blank, use the start date only (since-date clause). If `userStartDate` is blank, ask for the date scope. State in chat which dates were used and that they came from the release.
   - A date scope given in the request always wins over the release's dates.
   - Since-date only → JQL clause: `status changed to "Done" after "<since> 00:00"`
   - Explicit range → JQL clause: `status changed to "Done" after "<start> 00:00" AND status changed to "Done" before "<end + 1 day>"`
   - **Both boundaries are day-inclusive, and a bare date does not do that.** In this JIRA, `after "2026-11-09"` excludes the whole of 11-09 and `before "2026-11-09"` also excludes it (verified 2026-11-19: an issue moved to Done on 11-09 at 14:24 was missed by `after "2026-11-09"`, found by `after "2026-11-09 00:00"`). So always write the start as `"<start> 00:00"` and the end as the following day's bare date, otherwise issues moved to Done on the first or last day are silently dropped.
3. **Resolve product scope** per the block above, producing either `component not in (...)` (default) or `component in (...)` (ALP IL named).
4. **Build and run the JQL** via the existing `search_issues` function in [jira_client.py](../../../test%201/jira_client.py) — do not modify that file. Note the fix version being applied is **not** part of this search query — it's what gets written in step 6, not a filter:
   ```powershell
   .\.venv\Scripts\python.exe -c "
   from jira_client import search_issues
   jql = 'project = TRSC AND status changed to \"Done\" after \"<since> 00:00\" AND component not in (\"ALP IL - Administration\", \"ALP IL - Operation\", \"ALP IL - Reservation\")'
   issues = search_issues(jql, max_results=200)
   for i in issues:
       comps = ', '.join(c.name for c in i.fields.components) if i.fields.components else 'none'
       fixv = ', '.join(v.name for v in i.fields.fixVersions) if i.fields.fixVersions else 'none'
       print(f'{i.key} | {i.fields.summary} | {comps} | existing fixVersions: {fixv}')
   "
   ```
5. **Zero matches** → say so plainly, stop here.
6. **Display the full matched list in chat** — Key (linked with `issue_url(<KEY>)` from jira_client.py, printed by the script), Summary, Component, existing fixVersion(s) — and **always wait for the user's explicit go-ahead** before writing anything to JIRA. Never apply the update in the same turn the list is first shown.
   - Flag any matched issue that already carries another version of the same release series (same name apart from the number, e.g. `Bistro Connect release 2` when tagging `release 3`). A release starts on the previous release's release date, so an issue moved to Done on that boundary day can fall in both windows; let the user decide whether it stays in the earlier release only.
   - In the same message, state the closing actions that follow the tagging, so the one go-ahead covers all of them: mark `<FIX_VERSION>` as released, and create `<NEXT_NAME>` starting `<previous release date>` with no release date (step 10/11). If the next name can't be derived (no trailing digits), say so now.
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
9. **Provide a shareable release notes link.** This JIRA instance is Server/Data Center (Tomcat-hosted), not Cloud — the Cloud-style `/projects/<KEY>/versions/<id>` URL 404s here. The correct page is `ReleaseNote.jspa`, which needs the numeric project id (not the key) and the version id:
   ```powershell
   .\.venv\Scripts\python.exe -c "
   from jira_client import jira, JIRA_URL
   project_id = jira.project('TRSC').id
   version_id = next(v.id for v in jira.project_versions('TRSC') if v.name == '<FIX_VERSION>')
   print(f'{JIRA_URL}/secure/ReleaseNote.jspa?projectId={project_id}&version={version_id}')
   "
   ```
   Share this link as the final line of the report from step 8 — don't wait for the user to ask for it separately.
10. **Mark the release as released** (last step of the tagging; covered by the go-ahead from step 6). Skip with a note if every issue failed to tag, or if it is already released. Only `released` is sent, so the dates stay as they are:
    ```powershell
    .\.venv\Scripts\python.exe -c "
    from jira_client import jira
    v = next(v for v in jira.project_versions('TRSC') if v.name == '<FIX_VERSION>')
    if v.released:
        print('already released, skipping')
    else:
        v.update(released=True)
        print('released:', jira.version(v.id).released)
    "
    ```
11. **Create the next release, n+1.** Take the release's name and increment its **last digit group**, whatever comes before it (`Bistro Connect release 3` → `Bistro Connect release 4`, `ALP IL 2.18.4` → `ALP IL 2.18.5`). Start date = the just-released version's `userReleaseDate`, **release date left blank**. The next name is a deliberate guess for names with dotted numbers — always show it in the step 6 message so the user can correct it before anything is written. Only when the name has no trailing digits at all, don't invent one: tell the user and skip. If the next name already exists, skip and say so.
    ```powershell
    .\.venv\Scripts\python.exe -c "
    import re
    from datetime import date, timedelta
    from jira_client import jira
    cur = next(v for v in jira.project_versions('TRSC') if v.name == '<FIX_VERSION>')
    m = re.match(r'^(.*?)(\d+)$', cur.name)
    if not m:
        raise SystemExit('NO_PATTERN: no trailing number in ' + cur.name)
    next_name = m.group(1) + str(int(m.group(2)) + 1)
    if next_name in [v.name for v in jira.project_versions('TRSC')]:
        raise SystemExit('EXISTS: ' + next_name)
    want = cur.userReleaseDate   # the date the Releases page shows
    new = jira.create_version(next_name, 'TRSC', startDate=want)   # no releaseDate: stays blank
    got = jira.version(new.id)
    print(got.name, 'start shown:', got.userStartDate, 'wanted:', want, 'release shown:', getattr(got, 'userReleaseDate', None))
    "
    ```
    **Read the start back and compare with the wanted date.** Verified 2026-11-24 (creating `Bistro Connect release 4`): passing `startDate='YYYY-MM-DD'` to `create_version` shows up as exactly that date in the UI (`userStartDate` and raw `startDate` both equal), so no correction is needed. Versions created or edited in the JIRA UI are the ones whose raw dates sit a day behind. Still read it back; if `userStartDate` ever differs from the wanted date, correct it once with `jira.version(new.id).update(startDate=<wanted minus 1 day>)`, read it back again, and report the final value. If it still differs, say so rather than looping.
12. **Report the closing actions**: the release now marked released, and the new release with its name, start date (as shown in JIRA) and blank release date.

## Notes
- Read step (`search_issues`) is read-only. The write steps are: `fixVersions` on the matched issues via `update_issue`/`jira.issue` (step 7), marking the release as released (step 10) and creating the next release (step 11) — do not touch `jira_client.py`, `story_parser.py`, or `coord_finder.py`, only call their existing functions.
- No auto-apply mode — this always pauses for confirmation before writing, since it's a bulk change to shared JIRA state run on a recurring cadence. If that changes later, add an explicit toggle (mirroring `/create`'s `AUTO_CREATE`) rather than silently skipping confirmation.
- Companion to `/search` (read-only lookup) — this skill is the bulk-write counterpart, scoped specifically to the recurring release-notes fixVersion tagging workflow rather than general-purpose bulk edits.
