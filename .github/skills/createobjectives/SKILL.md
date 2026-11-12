---
name: createobjectives
description: 'Create the team''s SAFe PI Objectives in JIRA (project LPDA, component TRS) for an upcoming PI from a priority-ordered list of team epics, via objectives_helper.py: one objective per epic, linked to it, with fixVersion, Iteration label, Planned Business Value, Target end and house-style summary/description. Use when the user shares the epics for the next PI and asks to create objectives, or types /createobjectives. Always shows the drafted objectives and waits for approval before creating anything.'
argument-hint: '<PI, e.g. 27.1> <epic keys in priority order> [ENV overrides]'
---

# Create PI Objectives

## When to Use
- The user shares the list of epics the team takes into the next PI and asks to create the objectives, or types `/createobjectives`
- Inputs, from the request or asked for if missing:
  1. **PI** — e.g. `27.1` (fixVersion becomes `LPDA - PI#27.1`)
  2. **Epics in priority order** — LPDA epic keys, highest priority first. If the user gives names instead of keys, look the keys up and confirm them before planning
  3. **ENV overrides** (optional) — every objective is `[PRD]` unless the user says `[DEV]` or `[UAT]` for a specific epic
  4. **Sprint list** (optional) — the user may share the PI's sprints; the helper also reads them from the TravelScript board (sprints named `<PI>-<N>`, e.g. `27.1-3`)

## Conventions (from the PI 26.4 objectives, e.g. LPDA-3307, LPDA-3313)
- Issue type **PI Objective** in **LPDA**, component **TRS**, reporter and assignee **the user** (the JIRA account of the token in `.env`), fixVersion `LPDA - PI#<PI>`
- Exactly one **relates to** link, to its epic
- Label `Iteration<N>`: the PI sprint holding the epic's last planned story (any N, e.g. `Iteration6`). The IP sprint is not an iteration
- **Planned Business Value** by priority: 10 for the first epic, then 1 less for each next one (9 epics → 10 down to 2)
- **Target end**: end date of the `Iteration<N>` sprint. **Committed**: `Committed`. Commitment Level is not on the create or edit screen; JIRA fills it
- **Summary**: `[ENV] <short outcome title>`, starting with a verb, e.g. `[PRD] Migrate to NLT Hotel Only`, `[DEV] OpenShift migration: DEV cluster validation`. Drop the epic's own bracket tags (`[NLT]`, `[APS]`, …)
- **Description**: one sentence, `We will <concrete deliverable>, <benefit: to … / enabling … / as the next step toward …>, by the end of iteration <N> [ENV]`. A short scope note may follow the deadline phrase (LPDA-3310 does this). Examples:
  - `We will fully support the use of NLT to fetch Hotel Only offer data, enabling the move away from our current CWS integration, by the end of iteration 2 [PRD]`
  - `We will validate Bistro Connect's deployment on our local OpenShift DEV cluster, as the next step toward eliminating our non-compliant cloud subscriptions, by the end of iteration 4 [DEV]`

## Procedure
1. **Plan (read-only)** with [objectives_helper.py](../../../test%201/objectives_helper.py):
   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe objectives_helper.py plan --pi <PI> <EPIC-1> <EPIC-2> ...
   ```
   It prints JSON: `fix_version_exists`, the PI's `iterations` (sprint, end date) and per epic its summary/description/status, `planned_bv`, `stories_per_iteration`, `stories_in_ip_sprint`, the resulting `iteration` and `target_end`, and any `existing_objectives` (TRS only — other teams link their own objectives to the same epics). More than 10 epics raises an error: ask the user for the values.
2. **Stop and tell the user** if `fix_version_exists` is false (don't create the version), or if `iterations` is empty or differs from a sprint list they shared (the board names may not follow `<PI>-<N>` yet).
3. **Draft the summary and description** for each epic from its summary and description, following the conventions above. Keep it to what the epic actually promises; don't invent scope.
4. **Show the draft in chat** as one table — PBV, Epic (linked, `<JIRA_URL>/browse/<KEY>`, plus its summary), Iteration (with the story count per iteration), Target end, Summary, Description — and list anything to decide underneath:
   - `iteration` is null (no stories in the PI's sprints yet): ask which iteration
   - `stories_in_ip_sprint` > 0: the epic runs into the IP sprint; ask whether to keep the last numbered iteration
   - `existing_objectives` is not empty: it will be skipped
   - the epic isn't an `Epic`, or is already `Done`
   **Always wait for the user's explicit go-ahead.** Never create in the same turn the draft is first shown. Apply their changes (wording, ENV, iteration, values) and show the changed rows again.
5. **Write the approved plan** to `test 1/drafts/objectives/PI<PI>-plan.json`:
   ```json
   {"pi": "27.1", "objectives": [
     {"epic": "LPDA-1234", "summary": "[PRD] ...", "description": "We will ..., by the end of iteration 4 [PRD]",
      "iteration": 4, "target_end": "2027-02-12", "planned_bv": 10}
   ]}
   ```
6. **Create**:
   ```powershell
   .\.venv\Scripts\python.exe objectives_helper.py create "drafts/objectives/PI<PI>-plan.json"
   ```
   Per entry it re-checks the house style (`invalid` = not created, with the problems), skips epics that already have a TRS objective for this PI (`skipped`), otherwise creates the objective and links it to the epic (`created`). One failure doesn't stop the others (`failed`, with the JIRA error).
7. **Report back**: a table of created objectives (key linked, PBV, Iteration, Summary), then any skipped, invalid or failed entries.

## Notes
- The only JIRA writes are `create_issue` and `create_issue_link` inside `objectives_helper.py create`; `plan` is read-only. Do not touch `jira_client.py`.
- The iteration rule only holds at planning time: stories that slip or carry over show up in later sprints, so re-running `plan` mid-PI gives later iterations than the labels. Labels keep the original plan and are not moved.
- No auto-create mode: objectives are shared, visible PI commitments, so this always pauses for approval. If that changes later, add an explicit toggle (like `/create`'s `AUTO_CREATE`).
- The post-demo update (Reviewing → Done / Partially Done, Actual Business Value, System Demos Confluence page) is a separate skill.
