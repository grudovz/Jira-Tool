---
name: comment
description: 'Add a comment to a JIRA issue via jira_client.py, auto-resolving any @name mentions to real JIRA users (including the special @ticket/@Ticket token, which resolves to the issue''s current assignee), auto-attaching any pasted image(s) from the triggering message, and auto-transitioning on Done or test failed when the comment says so. Use when the user types /comment or asks to "add a comment"/"comment on" a JIRA issue without restating the issue key — resolve the key from the most recently discussed/retrieved issue in this conversation.'
argument-hint: '[comment text]'
---

# Add JIRA Comment

## When to Use
- User invokes `/comment` or asks to post/add a comment to a JIRA issue
- The issue key is often omitted — it must be resolved from conversation history

## Procedure
1. **Resolve the issue key**:
   - Use the key explicitly stated in the current request, if any (e.g. `TRSC-2898`).
   - Otherwise, scan this conversation for the most recently retrieved/discussed JIRA issue key (look for JIRA links, or prior `get_issue`/`add_comment`/`update_issue` calls).
   - Never invent a key. If none can be found, ask the user which issue to comment on.
2. **Resolve the comment text**: everything the user wrote after `/comment`. If blank, ask the user what to comment.
3. **Resolve `@name` mentions** — the user has given standing approval to do this automatically, without asking per-comment:
   - Find every `@name` token in the comment text (e.g. `@al`, `@aleksis`).
   - **Special case — `@ticket`/`@Ticket` (case-insensitive, exact token match)**: resolves to the current assignee of the issue being commented on (the key resolved in step 1), not a name search. Fetch the issue via the existing `get_issue` function in [jira_client.py](../../../test%201/jira_client.py) and read `issue.fields.assignee.name`. If assigned, replace the token with `[~<assignee.name>]`, same as a resolved name mention. If the issue is unassigned, treat it like a zero-match name (leave the literal token in the text and report back that the ticket has no assignee).
   - For every other `@name` token, look up JIRA users via the `jira` client instance already exported by [jira_client.py](../../../test%201/jira_client.py) (`from jira_client import jira`) — do not modify that file:
     ```python
     jira.search_users(user="<name>", includeInactive=False)
     ```
     (This instance is JIRA Server/Data Center — use the `user=` parameter, not `query=`.)
   - **Exactly one match**: replace `@name` in the text with `[~<user.name>]` (the matched user's username field — this is the mention syntax this JIRA instance actually renders, confirmed against existing comments like `[~asideris]`). Do this automatically; no confirmation needed.
   - **Zero or multiple matches**: don't guess — leave `@name` as literal text in the posted comment, and afterward tell the user it couldn't be resolved (listing candidates' display names/usernames if there were multiple, so they can be more specific next time).
4. **Post the comment** (with any resolved mentions substituted in) using the existing `add_comment` function in [jira_client.py](../../../test%201/jira_client.py) — do not modify that file. Run it through the project's venv, e.g.:
   ```powershell
   cd "test 1"
   .\.venv\Scripts\python.exe -c "from jira_client import add_comment; add_comment('<KEY>', '<TEXT>')"
   ```
   If the comment text contains quotes, newlines, or other characters that break PowerShell quoting, write a small temp script under `$env:TEMP` instead, import `add_comment` (and `jira` for mention lookups) via `sys.path`, run it, then delete the temp file.
5. **Attach any pasted image(s)** — see [Attachment handling](../../copilot-instructions.md#attachment-handling) in copilot-instructions.md; standing approval, no need to ask. If the message that triggered this `/comment` (or an ad-hoc "add a comment" request) includes one or more pasted images, attach each one to the same issue key via `attach_file` in [jira_client.py](../../../test%201/jira_client.py), passing the image's file path directly:
   ```powershell
   .\.venv\Scripts\python.exe -c "from jira_client import attach_file; attach_file('<KEY>', r'<IMAGE_PATH>')"
   ```
   No image attached to the triggering message → skip this step silently, don't mention it.
6. **Check for status transition signals** — the user has given standing approval for auto-transitions on Done and test failed, no need to ask each time:
   - **Done/approved**: If the comment text clearly states the issue should now be considered done/approved/closed (e.g. "moving to done", "move to done", "marking as done", "marking as approved", "this is approved", "closing as done") — as a verdict on the ticket, not incidental use of the word — transition it via `transition_issue('TRSC-...', 'Done')`.
   - **Test failed**: If the comment text clearly states the issue should move to test failed (e.g. "moving to test failed", "test failed", "marking as test failed") — as a verdict on the ticket — transition it via `transition_issue('TRSC-...', 'Verify')`.
   - Reference the JIRA status mapping table in [copilot-instructions.md](../../copilot-instructions.md) to map internal status names to JIRA status names when transitioning.
   - Use the existing `transition_issue` function in [jira_client.py](../../../test%201/jira_client.py):
     ```powershell
     cd "test 1"
     .\.venv\Scripts\python.exe -c "from jira_client import transition_issue; transition_issue('<KEY>', '<JIRA_STATUS>')"
     ```
   - Don't trigger on negated or uncertain phrasing (e.g. "not done yet", "can't confirm this is done", "isn't done") — if genuinely ambiguous whether the user means to transition, don't guess: post the comment as normal and ask before transitioning.
7. **Confirm** back to the user which issue key was commented on, the exact text posted (with mentions already resolved shown as who they resolved to), any `@name` that couldn't be resolved, any image(s) attached, and whether the status was also transitioned (and to what).

## Notes
- This mirrors the manual steps already used in this project for TRSC-2898 comments/description updates.
- Do not touch `jira_client.py`, `story_parser.py`, or `coord_finder.py` — only call the existing `add_comment`/`transition_issue`/`attach_file` functions and the module-level `jira` client instance it already exports.
- Mention resolution only ever *substitutes text the user already asked for* (a name they typed as `@name`, or the `@ticket` token) — it never adds a mention the user didn't type, and ambiguous/unresolved names are reported, never guessed.
- The transition checks are judgment-based (this skill is read and executed by an LLM, not a strict regex), same as resolving the issue key or deciding when `/comment` was invoked — favor precision over recall: skip the transition on anything genuinely ambiguous rather than changing a ticket's status incorrectly.
