---
name: analyse
description: 'Analyse a draft story, or business/technical requirements provided in this session, and return a single Suggestions section (suggested changes, missing information, other remarks), grounded in the actual client/server code and UI screenshots where available, and in an existing JIRA issue if one is referenced. Use when the user asks to "analyse", "review", or "check" a story/requirements, or types /analyse. Output goes to chat only, for iterative back-and-forth — this skill never writes a file or touches JIRA.'
argument-hint: '[pasted requirements/story text or issue-key]'
---

# Analyse a Draft Story or Requirements

## When to Use
- The user pastes a draft story, or business/technical requirements, and asks for analysis/review/feedback — or types `/analyse`
- Goal: produce grounded, structured feedback in chat, so the user can iterate with follow-up messages before anything is finalized — not a one-shot report, and not a file

## Context sources
1. **Session input** — the primary source: whatever draft story or requirements text the user pasted/wrote in this conversation (the most recent, unless they point at something earlier).
2. **JIRA fields** — only if an issue key is given or already being discussed in this conversation: summary, description, comments via `jira_client.get_issue` in [jira_client.py](../../../test%201/jira_client.py). An issue key is optional — the input may be pre-story requirements that don't exist in JIRA yet.
3. **Code** — the `trsc-client` and `trsc-gateway` folders, available when [jira-story-tool.code-workspace](../../../jira-story-tool.code-workspace) is open as a multi-root workspace. Use `semantic_search`/`grep_search` scoped to those folders per the [Code-grounding scope](../../copilot-instructions.md#story-writing-conventions): only to check feasibility of the requirement and surface unaddressed technical limitations/dependencies, never to derive implementation-level recommendations.
4. **Screenshots** — `test 1/analysis-context/<feature>/current/` (actual UI state) and `test 1/analysis-context/<feature>/reference/` (design/target mockups), if present. Use the image-viewing tool on any files found there. This folder is gitignored — it's local context only.
5. **Story Writing Conventions** — the team conventions list in [copilot-instructions.md](../../copilot-instructions.md#story-writing-conventions); check the input against these explicitly (e.g. acceptance criteria present in the description).

## Procedure
1. **Resolve the input**: the draft story or requirements text most recently pasted/discussed in this session. If an issue key is also given or already discussed, treat it as an additional grounding source (fetch via `get_issue`); if not, just proceed on the pasted text alone — don't call out the missing key, the user doesn't need to be told.
2. **Identify the feature/component** the input is about (used to search code and locate a screenshot folder).
3. **Search the code** (if the multi-root workspace is open): check whether the requirement is feasible against the current architecture/data model, and note any technical limitation or dependency relevant to the story that it doesn't already address. Don't derive or report implementation-level guidance (specific files/functions/migrations to change). If the workspace isn't open (only the Macros folder is), just proceed without code-grounding — don't call this out, the user doesn't need to be told.
4. **Check for screenshots** under `test 1/analysis-context/<feature>/current/` and `.../reference/`. View any found. If none exist, just proceed on code + text alone — don't call out the missing screenshots, the user doesn't need to be told.
5. **Check against Story Writing Conventions** — flag gaps in required content only (e.g. no acceptance criteria in the description). Never flag the Background or Technical Details sections as missing — they're optional by convention, not gaps.
6. **Produce the analysis in chat as a single Suggestions section** — bundle suggested changes, missing information, and other remarks about the story together (clarity, completeness, and scope observations all fold into this one section rather than being split into separate headings), grounded in what the code/screenshots/conventions actually show. Code-grounded points belong here only when they affect feasibility or surface an unaddressed technical limitation/dependency (e.g. "NLT doesn't currently expose this field" or "the current screenshot shows Z, which doesn't match the reference design") — never as an implementation recommendation (e.g. don't say "extend function X in file Y" or "add a migration like Z").

## Notes
- Never fabricate a code reference or screenshot observation — only cite what was actually found via search/read/view.
- Code findings are for feasibility/limitation checks only, per [Code-grounding scope](../../copilot-instructions.md#story-writing-conventions) — never recommend specific files, functions, classes, or migrations for developers to change; that's implementation, not analysis.
- This skill only ever outputs to chat — it never writes a file and never touches JIRA. Writing the file is `/draft`'s job (and `/draft` no longer pushes to JIRA either — see its SKILL.md).
- Don't end responses by prompting the user to use `/draft` — they know it's available; no reminder needed.
