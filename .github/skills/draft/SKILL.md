---
name: draft
description: 'Echo the current best version of a story (my latest analysis/response, your latest input, or your specific instructions — whichever applies) in chat, then write it to the scratch file test 1/drafts/item.md for dictation-friendly review/editing, and register that file so it can be opened directly from the chat/file picker rather than Explorer. Use when the user asks to "draft this", "save this to a file", or types /draft. This skill does not update JIRA.'
argument-hint: '[optional instructions]'
---

# Draft a Story to a Scratch File

## When to Use
- The user wants the current story content saved to a real editor file they can open and dictate corrections into (Dragon-compatible, unlike the read-only chat transcript) — or types `/draft`
- This is the natural next step after `/analyse`, once the user is happy with where the chat discussion has landed, but it can also be invoked on its own, driven purely by explicit instructions
- Invoking `/draft` (or saying "save this to a file") is itself the explicit request to write the file — this skill isn't used for chat-only drafting. Ad-hoc collaborative drafting (raw input → Background/AC in chat → "go") stays chat-only and never touches this file unless the user separately asks for it.

## Resolving the source content
Pick exactly one, in this priority:
1. **Explicit instructions or text given with this invocation** (e.g. "/draft use this version instead: ...") — use that verbatim.
2. **Whichever of my last response or your last message is more recent and is the story content itself** — e.g. if I just gave an analysis/rewrite and you haven't replied since, use my response; if you just pasted a revised version, use yours instead.
3. If neither is clearly the intended source, ask which content to draft rather than guessing.

Apply the [Story Writing Conventions](../../copilot-instructions.md#story-writing-conventions) when assembling the content (e.g. make sure acceptance criteria are included in the description) — but never invent details the source didn't provide; if a convention can't be satisfied from what's there, flag the gap in your reply instead of fabricating content. Per [Code-grounding scope](../../copilot-instructions.md#story-writing-conventions), keep any Technical Details at the business/data level (external systems, data fetched, mapping to UI elements) — never file paths, function/class names, or other implementation-level references pulled from code.

Any formatting applied to the text (bold section headings, bullet lists, etc.) must use JIRA wiki markup syntax (e.g. `*bold*`, `* item` bullets — not `-`, which JIRA renders as strikethrough), not Markdown — this file's content is meant to transfer straight into a JIRA description later, so it must already be formatted the way JIRA itself renders it.

## Procedure
1. Resolve the source content as above.
2. **Echo the resolved content in chat first**, rendered as real Markdown (same as everywhere else this project shows JIRA wiki markup) — so the user can see exactly what's about to be saved without opening the file.
3. Run `/analyse` against this content. Fold a gap it surfaces directly into the content **only when the fix is mechanical/non-judgment** — applying an already-established convention or an existing fallback pattern used elsewhere. Stay conservative here: anything that actually requires a decision (exact wording, event granularity, scope) must NOT be folded in — surface it instead as an explicit open question right below the echoed draft, and don't write it into the file until the user resolves it.
4. Write the (possibly gap-folded) content to `test 1/drafts/item.md` (fixed filename — this file is reused for whatever story is currently being worked on, not per-issue). Overwrite any existing contents.
5. If `item.md` already existed with different content, mention that it was overwritten, in case the user had unfinished edits there.
6. Register the file via `add_artifact_or_reference` (`type: 'file'`, `isArtifact: true`, pointing at `test 1/drafts/item.md`) so it shows up as an openable link next to the chat input, instead of the user having to find it in Explorer.
7. Tell the user the file is ready to open/dictate over. Pushing its contents into a JIRA issue's description is a separate, explicit step this skill doesn't do automatically — say so, so they know to ask for that when ready (e.g. "update the issue description with item.md").

## Notes
- Do not touch `jira_client.py`, `story_parser.py`, or `coord_finder.py` — this skill doesn't call any of them.
- `test 1/drafts/` is gitignored — scratch only.
