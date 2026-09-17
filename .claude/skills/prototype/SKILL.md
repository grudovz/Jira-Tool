---
name: prototype
description: 'Build a static HTML/CSS UI prototype for a JIRA story, grounded in the real trsc-client component source (markup/classes/tokens/icons) rather than invented styling, saved under test 1/drafts/mockups/. Use when the user asks to "create a UI prototype", "mock this up", "build a prototype for this story", wants a low/medium-fidelity mockup of a feature, or types /prototype. Companion to /draft (text) and /analyse (requirements) — this is the code-grounded visual counterpart.'
argument-hint: '[story key or short description of the UI to prototype]'
---

# Build a UI Prototype

## When to Use
- The user wants a visual mockup of a UI change/feature described in (or planned for) a JIRA story, and there's no dedicated design resource / no existing design file covers it
- Phrases like "mock this up", "build a prototype", "what would this look like", or `/prototype`
- Not for the Streamlit UI (`app.py`) — that tool is on hold per [copilot-instructions.md](../../copilot-instructions.md); this skill is exclusively for prototyping the **trsc-client** (Bistro Connect) product UI

## Ground rule
Never invent styling. Every color, font, class, icon, and piece of copy in the prototype should trace back to something real: the actual `trsc-client` source, the story's own text, or an existing design file (XD) — or it must be visibly flagged as a guess/placeholder. This mirrors the "don't invent, signal absence" rule already used by `/draft` and `/analyse`.

## Procedure
1. **Scope the UI.** Identify the story key (if any) and exactly which page/component/state is being prototyped. If ambiguous (which page, which state, expanded vs. collapsed), ask rather than guessing.
2. **Find the real source.** `../BC/trsc.service-center-client` is the sibling SvelteKit repo (see [reference_trsc_client_source] in memory) — it is the grounding source of truth, preferred over the XD design or a written description alone when the two disagree, since it reflects what's actually live. Locate the relevant `.svelte` component(s) via Grep/Glob (route names, button labels, known component names) rather than guessing file names. Prefer targeted `Grep` over reading an entire large file when only a specific block (a button, a form section) is needed — full-file reads are expensive and usually unnecessary.
   - When a class is conditional (Svelte `class:x={cond}`, a ternary inside a template string, or anything with Tailwind's `!important` modifier like `!bg-[#E6EFF8]`), read that literal line yourself rather than relying on a subagent's paraphrase — `!important` overrides mean the condition *replaces* a base/status color rather than blending with it, and that precedence is easy to lose in a summary.
3. **Extract real tokens, not approximations:**
   - Colors/fonts: `src/css/custom.css` (`:root` custom properties, base `html` font-size) and `tailwind.config.js` (confirm whether the default Tailwind scale applies or is overridden).
   - Icons: `src/assets/icons/*.svg` — inline the real SVG `<path>` markup as `<symbol>`/`<use>` in the prototype (with `fill: currentColor`) so icons can be recolored per context. Never substitute emoji for icons — they render at the wrong weight/color and are the single biggest visual-fidelity gap seen so far.
   - Fonts/logo already copied into `test 1/drafts/mockups/fonts/` and `test 1/drafts/mockups/bistro-connect-logo.svg` from earlier prototypes — reuse them, don't re-copy.
4. **Build a single static HTML file** (inline `<style>`, no build step) at `test 1/drafts/mockups/<story-key>-<short-name>.html` (fixed folder — gitignored scratch, same convention as `/draft`'s `test 1/drafts/item.md`). Reuse assets already present in that folder before copying new ones in.
5. **Flag anything not sourced from real code/design inline, at the specific element it applies to** — a small badge/note next to a guessed piece of copy or a simplified/placeholder section (e.g. "not from `TileTableView.svelte`, simplified placeholder"), so a developer opening the raw file cold still knows what to trust. Do **not** add a summary/changelog paragraph at the top or a disclaimer footer at the bottom explaining what the prototype is or what changed since the last version — that narrative belongs in the chat response, not in the file itself.
   - If the story already has a real design file (e.g. an XD link in the issue's **Design** section per [Story Writing Conventions](../../copilot-instructions.md#story-writing-conventions)), check it before flagging copy as an unconfirmed guess. Copy that's actually shown in that design is *sourced*, not invented — link to the design inline instead of a "propose for confirmation" disclaimer. Reserve the "not found verbatim, propose for confirmation" wording for copy that isn't backed by the code *or* an existing design.
6. **Verify visually before calling it done.** Open the file with `mcp__client__openBrowserPage`/`navigatePage` (`file:///` URL) and capture it with `mcp__client__screenshotPage`. If the user supplies a real reference (a live-app screenshot or XD link), compare directly and call out *specific* differences (icon choice, spacing, disabled/enabled states, missing elements) — per the "narrate investigation findings" behavior, explain the diagnosis in chat, don't let a silent file edit stand in for it.
   - Treat a supplied reference screenshot as the full spec to replicate, not just a check on the one element you set out to build. Don't simplify or placeholder a section just because it feels tangential to the story's ask — if the screenshot shows it in full, reproduce it in full.
   - Before declaring the mockup done, do one explicit region-by-region pass against the reference (background/border, each row/column band, buttons, icons, toggle states) rather than eyeballing the whole image at once — real gaps (e.g. a band's actual background color, a single-row-vs-stacked layout) are easy to miss on a first holistic look and only surface once you check region by region.
   - If a live/dev `trsc-client` instance is reachable, ask early whether you can view it directly for pixel-level comparison instead of working only from a static screenshot.
7. **Iterate with targeted `Edit` calls**, not full-file rewrites, once the initial structure is confirmed — cheaper and keeps the diff reviewable.
8. **Attaching to JIRA is an explicit, separate step — never automatic:**
   - When the user says the prototype is ready and asks to attach it to a specific issue, attach the **raw `.html` file** directly via `attach_file` in [jira_client.py](../../../test%201/jira_client.py) (do not modify that file) so developers can open the real file locally and inspect it, rather than only seeing a flattened image:
     ```powershell
     cd "test 1"
     .\.venv\Scripts\python.exe -c "from jira_client import attach_file; attach_file('<KEY>', r'test 1/drafts/mockups/<file>.html')"
     ```
   - Screenshots of the prototype (full-page or specific sections/states) are captured and uploaded by the user manually, only when they decide to — this skill does not generate or attach screenshots to an issue on its own.
   - If the story's description has a **Design** section (per [Story Writing Conventions](../../copilot-instructions.md#story-writing-conventions)), mention that the attached prototype filename should be referenced there too, so a developer knows which attachment to open.

## Notes
- Do not touch `jira_client.py`, `story_parser.py`, `bug_parser.py`, or `coord_finder.py` — only call the existing `attach_file` function, and only when explicitly asked to attach.
- `test 1/drafts/` (including `mockups/`) is gitignored — these are scratch/reference artifacts, not committed deliverables.
- These prototypes are point-in-time snapshots of `trsc-client`'s source at build time — they do **not** auto-update if the real codebase changes later. Before reusing an existing prototype file as the base for a new story, re-check that the classes/components it cites still exist; don't assume it's still accurate just because it was accurate when built.
- Token efficiency matters here: grep for the specific markup needed instead of reading whole multi-hundred-line source files, use `Edit` instead of rewriting the whole HTML file on each revision, and take targeted screenshots (only the changed region) once the base layout is settled rather than a full-page screenshot every iteration.
- Companion to `/draft` (assembles the JIRA description text) and `/analyse` (code-grounded requirements analysis) — this is the code-grounded *visual* counterpart, for stories where a written description or an XD link alone isn't enough to align on what the UI should look like.
