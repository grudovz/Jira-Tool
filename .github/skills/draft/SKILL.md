---
name: draft
description: 'Write the current best version of a story (my latest analysis/response, your latest input, or your specific instructions — whichever applies) to the scratch file test 1/drafts/item.md for dictation-friendly review/editing. Use when the user asks to "draft this", "save this to a file", or types /draft. This skill only writes the file — it does not update JIRA.'
argument-hint: '[optional instructions]'
---

# Draft a Story to a Scratch File

## When to Use
- The user wants the current story content saved to a real editor file they can open and dictate corrections into (Dragon-compatible, unlike the read-only chat transcript) — or types `/draft`
- This is the natural next step after `/analyse`, once the user is happy with where the chat discussion has landed, but it can also be invoked on its own, driven purely by explicit instructions

## Resolving the source content
Pick exactly one, in this priority:
1. **Explicit instructions or text given with this invocation** (e.g. "/draft use this version instead: ...") — use that verbatim.
2. **Whichever of my last response or your last message is more recent and is the story content itself** — e.g. if I just gave an analysis/rewrite and you haven't replied since, use my response; if you just pasted a revised version, use yours instead.
3. If neither is clearly the intended source, ask which content to draft rather than guessing.

Apply the [Story Writing Conventions](../../copilot-instructions.md#story-writing-conventions) when assembling the content (e.g. make sure acceptance criteria are included in the description) — but never invent details the source didn't provide; if a convention can't be satisfied from what's there, flag the gap in your reply instead of fabricating content. Per [Code-grounding scope](../../copilot-instructions.md#story-writing-conventions), keep any Technical Details at the business/data level (external systems, data fetched, mapping to UI elements) — never file paths, function/class names, or other implementation-level references pulled from code.

## Procedure
1. Resolve the source content as above.
2. Write it to `test 1/drafts/item.md` (fixed filename — this file is reused for whatever story is currently being worked on, not per-issue). Overwrite any existing contents.
3. If `item.md` already existed with different content, mention that it was overwritten, in case the user had unfinished edits there.
4. Tell the user the file is ready to open/dictate over. Pushing its contents into a JIRA issue's description is a separate, explicit step this skill doesn't do automatically — say so, so they know to ask for that when ready (e.g. "update the issue description with item.md").

## Notes
- Do not touch `jira_client.py`, `story_parser.py`, `coord_finder.py`, or `glossary.py` — this skill doesn't call any of them.
- `test 1/drafts/` is gitignored — scratch only.
