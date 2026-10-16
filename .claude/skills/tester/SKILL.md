---
name: tester
description: 'Test a JIRA ticket''s acceptance criteria or expected results on Bistro staging by running the user-level `tester` subagent, which has its own headless Playwright browser that loads only for this skill. Show its pass/fail report. After the user''s feedback, attach the evidence screenshots, post the findings as a new JIRA comment and transition the ticket. Use when the user types /tester or asks to test, verify or check a ticket''s ACs on staging.'
argument-hint: '[issue key or number, plus optional focus notes]'
---

# Test a Ticket on Staging

## When to Use
- The user invokes `/tester <key>`, or asks to test, verify or check a ticket's ACs (or a bug's expected result) on staging.
- One ticket per run. For several tickets, run them one after another.

## Procedure
1. **Resolve the issue key:**
   - Accept a full key (e.g. `TRSC-2992`) or shorthand digits. Prefix digits with `DEFAULT_PROJECT` from [jira_client.py](../../../test%201/jira_client.py).
   - Never guess; ask if no key is given.
   - Pass anything else the user wrote (focus areas, setup hints, checks to skip) on to the agent.
2. **Run the `tester` subagent in the foreground:** use the Agent tool with `subagent_type: "tester"` and `run_in_background: false`, because the user is waiting and background results get lost. The prompt is the key plus the user's notes. The agent:
   - reads the ticket;
   - checks the fix is deployed on staging;
   - derives regression checks from the fix's diff;
   - tests in its own headless browser;
   - saves screenshots to `test 1/drafts/ac-verify/<KEY>/`;
   - returns a report. It never writes to JIRA.

   If the agent type isn't found, either `~/.claude/agents/tester.md` is missing or this chat started before it existed; the user needs a new chat. Don't fall back to testing in the main chat unless the user asks.
3. **Show the report.** The user can't see the agent's reply, so relay it in full: table, things noticed, for you to check, staging data changed. Register each screenshot via `add_artifact_or_reference` (`type: 'file'`, `isArtifact: true`, `label: "<KEY> evidence: <filename>"`, `uri` = its `file://` path) so it's clickable.
4. **Wait for the user's feedback.**
   - Don't ask before or during testing. The report states its judgement calls, and the user confirms them afterwards.
   - For follow-up checks (e.g. "re-check 3 at 375px"), use `SendMessage` to the same agent. It keeps its context, and its browser restarts logged in.
5. **After the feedback, post to JIRA.** This has standing approval; don't confirm again.
   1. Attach every screenshot the report used, via `attach_file` in [jira_client.py](../../../test%201/jira_client.py).
   2. Post **one new comment** via `add_comment`, in the format below, with the user's corrections applied (changed verdicts, dropped items). Never edit an existing comment that embeds images.
   3. Transition per the user's verdict via `transition_issue`:
      - done or approved → `'Done'`
      - test failed → `'Verify'`
      - no clear verdict → post without transitioning, then ask.

   Write the calls into a temp script under `$TEMP`, because quotes and newlines break one-liners. Run it with the venv Python from `test 1`, then delete it.
6. **Confirm back:** the key (as a `/agile/browse/<KEY>` link), the attachments, the comment posted and the new status.

## Comment format (JIRA wiki markup)
```
h3. Test results on staging (<fe> / <gw>)
||#||Check||Result||Notes||
|1|<check>|(/) Pass|<notes>|
|2|<check>|(x) Fail|<notes>|
|3|<check>|(?) Can't verify|<notes>|

*Other things noticed*
* <item>

*Evidence (attached)*
!<file1>.png|thumbnail! !<file2>.png|thumbnail!

Moving to Done.
```
- `(/)`, `(x)` and `(?)` render as icons. Leave out "For you to check" items unless the user wants them recorded.
- **Markup traps in plain text:**
  - `+x+` underlines and `-x-` strikes through;
  - `~x~` and `^x^` become sub- and superscript;
  - `[x]` becomes a link and `{x}` a macro;
  - `|` breaks a table cell, and `*` turns text bold.

  Rephrase instead of escaping: "1.5 to 2.5 px" rather than "1.5-2.5 px", and "plus" rather than `+`.
- Never include the staging login URL or its token.

## Notes
- **Why the agent lives at user level:** it's `~/.claude/agents/tester.md`, not in this repo, because its Playwright MCP server is defined inline. The server starts with the agent and stops when the agent ends, so normal chats (editing tickets etc.) never load the browser or its ~5k tokens of tool definitions. Claude Code only loads inline MCP servers from a project's `.claude/agents/` if the folder is trusted, and SDK sessions don't count as trusted; user-level agents don't need trust.
- **Playwright setup:** Playwright MCP is installed at `~/.claude/tools/playwright-mcp/`, pinned and run with `node` rather than npx. `staging-login.js` in that folder logs each new tab into staging from `test 1/.env`, so the agent never sees the token. `--secrets` redacts the login URL from tool output.
- **Name:** the skill is `/tester`, not `/verify`, because "Verify" is the JIRA status for test failed.
- **Agent scope:** the agent may change staging data freely, and the report lists what changed. Production and JIRA are out of scope for it.
- **Copilot:** there's no `tester` subagent there. Follow the procedure in `~/.claude/agents/tester.md` directly in chat with the available browser tool.
