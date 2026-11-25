---
name: systemdemo
description: 'Before and after each SAFe system demo: list the team''s (TRS) PI Objectives that are in status Reviewing on the PI''s "System Demos" Confluence page under the upcoming demo, then after the demo set their Actual Business Value, move them to Done or Partially Done in JIRA and fill the ABV on the page. Via objectives_helper.py and the mcp-gateway Confluence tools. Use when the user asks to add/prepare objectives for the system demo, to close objectives after the demo, or types /systemdemo. Always shows the planned changes and waits for approval before writing to JIRA or Confluence.'
argument-hint: 'before|after <PI, e.g. 26.4> [page link] [after: <KEY> Done|Partially Done [ABV] ...]'
---

# System Demo: PI Objectives

Two runs per system demo:
- **before** — add every TRS objective of the PI that is in **Reviewing** to the upcoming demo's section of the PI's System Demos page, with `ABV:` left empty
- **after** — with the status and ABV the user gives per objective: set **Actual Business Value**, move it **Reviewing → Done / Partially Done**, and fill the ABV on its page line. All other transitions are done by the user, manually

## Inputs
- **PI** — e.g. `26.4`; objectives are found by fixVersion `LPDA - PI#<PI>`, component `TRS`, status Reviewing
- **System Demos page** — the user gives the link once per PI (e.g. `https://<site>.atlassian.net/wiki/spaces/<SPACE>/pages/<id>/PI+26.4+-+System+Demos`). Reuse it from the conversation if already given; otherwise ask. Don't search for it
- **after only** — per objective: `Done` or `Partially Done`, and the ABV. If the user says Done without an ABV, use the PBV; for Partially Done, ask for the ABV if it's missing

## Page structure (read as HTML)
- A JIRA table macro at the top lists every team's Reviewing objectives; it updates itself, never touch it
- One section per demo, newest first: `<h2>System Demo <PI>-<N> <time datetime="YYYY-MM-DD">…</time></h2>`, then `<h3>PI Objectives</h3>` followed by one or more `<ul>`s of **team items**. A team item is `<li><p>TEAM</p><ul>…objective lines…</ul></li>`; ours is `TRS`. The last demo section also has `<h3>Innovation</h3>` — not ours
- An objective line is `<li><p>` + inline Jira Legacy macro (`data-extension-key="jira"`, key in `macroParams.key.value`) + ` (PBV: n, ABV: m)` `</p></li>`. Our lines have no @mention
- Every node has a `data-local-id`; edits target nodes by it

## Before the demo
1. **List the objectives** (read-only):
   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe objectives_helper.py reviewing --pi <PI>
   ```
   Returns each objective (key, summary, labels, `planned_bv`, `line_html`) and `team_item_html` (all lines under a `TRS` item). No objectives → say so and stop.
2. **Read the page** with the Confluence tool `getConfluenceContent` (mcp-gateway, `cloudId` = the page link's host, e.g. `<site>.atlassian.net`): `content_url` = the page link, `content_format: html`, `detail: full`, `draft: true`. Keep the returned `snapshotToken`.
3. **Pick the demo**: the section with the earliest `<time datetime>` that is today or later. None → ask the user which section.
4. **Work out the edits** inside that section only (from its `<h2>` to the next `<h2>`):
   - Skip objectives whose key is already on a line in the section. If a key is on a line in another demo section, flag it — don't add it twice without the user saying so
   - **TRS item exists** → `insertNodeAfter` the last `<li>` of its nested `<ul>`, `value` = the objective's `line_html`. For several objectives, insert them after that same anchor in reverse order so they end up in key order
   - **No TRS item, and the section's only team item is a placeholder** (e.g. `Team …`, no nested list) → `replaceNode` on that placeholder `<li>` with `team_item_html` (built from the objectives still to add)
   - **No TRS item, other teams present** → `insertNodeAfter` the last team `<li>` of the section's last PI Objectives `<ul>`, `value` = `team_item_html`
5. **Show the plan in chat** — demo (name and date), and per objective: key (linked with the `url` that `objectives_helper.py` returns), summary, the line text `KEY (PBV: n, ABV: )`, and the action (new TRS item / added to TRS item / replaces placeholder). **Wait for the user's go-ahead.** Never write in the same turn the plan is first shown.
6. **Save** with `updateConfluenceContent`: `contentId`, `snapshotToken`, `edits`, `versionMessage: "TRS objectives for System Demo <PI>-<N>"`. Don't use `dryRun` (it echoes the whole page). On `snapshot_stale`, re-read the page (step 2) and redo step 4 before retrying.
7. **Verify and report**: re-read the page as markdown and confirm the lines sit under the right demo; report the demo, the objectives added and the page link.

## After the demo
1. **Confirm the closing list in chat** — per objective: key, summary, PBV, new status, ABV. **Wait for the user's go-ahead.**
2. **Write** `test 1/drafts/objectives/PI<PI>-close.json`:
   ```json
   {"objectives": [{"key": "LPDA-3307", "status": "Done", "actual_bv": 9}]}
   ```
3. **Update JIRA**:
   ```powershell
   .\.venv\Scripts\python.exe objectives_helper.py close "drafts/objectives/PI<PI>-close.json"
   ```
   Per entry it sets Actual Business Value, then transitions (`closed`, with `line_html` holding the filled-in page line). It skips objectives no longer in Reviewing (`skipped`) and refuses any status other than Done / Partially Done (`invalid`). One failure doesn't stop the others (`failed`).
4. **Update the page** for every `closed` entry: read the page (as in Before step 2), find the objective's line inside a `TRS` item (normally in the demo section just held), and `replaceNode` on that line's `<li>` with its `line_html`. Send all edits in one `updateConfluenceContent` call, `versionMessage: "TRS objectives ABV after System Demo <PI>-<N>"`.
5. **Verify and report**: re-read the page as markdown; report per objective the new status, ABV and page line, plus anything skipped or failed.

## Notes
- JIRA writes happen only in `objectives_helper.py close` (Actual Business Value + the Done / Partially Done transition). Do not touch `jira_client.py`.
- The page is shared with every team in the ART: only ever edit TRS items and lines (or the placeholder when TRS is the first team in a section). Never rewrite the whole body, never touch other teams' content, the top table or Innovation.
- New lines get the same macro settings as the existing TRS lines (`demo_line` in the helper). The JIRA server name and id the macro needs come from `CONFLUENCE_JIRA_SERVER` / `CONFLUENCE_JIRA_SERVER_ID` in `test 1/.env`. Confluence assigns `macroId` and the local IDs itself.
- Companion to `/createobjectives`, which creates the objectives at the start of the PI.
