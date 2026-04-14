# Jira Ticket Template — Outbound Feed Failure

This template applies to all accounts. Fill in account-specific values from the resolved config.

## Project Details
- **Board:** Per config (`jira_project_key`). Production default: `DT` (Data Team).
- **Instance:** Per config (`jira.instance`)
- **Issue Type:** Task

---

## Ticket Fields

### Summary
```
[<ACCOUNT> Outbound] Feed Export Failure — <YYYY-MM-DD>
```
Example: `[<ACCOUNT> Outbound] Feed Export Failure — 2026-03-23`

### Description

```
## Issue Summary
The <ACCOUNT> outbound feed export failed on <DATE> (<DAY OF WEEK>).

**Feed types affected:**
- [ ] <Feed Type 1>: <list failed source tables, or "Not affected">
- [ ] <Feed Type 2>: <list failed source tables, or "Not affected">
- [ ] <Feed Type N>: <list failed source tables, or "Not affected">

**Report date range:** <Report From> to <Report To>
**Emails expected:** <N> | **Emails received:** <N>
**Failed files:** <total count>

---

## Workflow Context
**Analytics (owner):**
- Detected the issue via automated outbound feed check (Claude Code scheduled task)
- Created this Jira ticket and posted the alert to <slack_channel>
- Leads all communication with the client data team on status and ETA
- Performs QA on backfilled data before it is sent to the client

**Data Engineering (investigator):**
- Investigates root cause of the pipeline failure
- Provides ETA and status updates in the Jira ticket and Slack thread
- Executes the fix and generates the backfill export
- Documents the fix steps, root cause, and any enhancement version log in the Jira notebook/comments

**Resolution flow:**
DE investigates → shares findings with Analytics → Analytics QAs backfill → Analytics sends to client → DE documents in ticket → ticket closed

---

## Success Criteria
- Root cause identified and fix applied by DE
- Backfill generated for the failed date range
- Backfill QA passed by Analytics (row counts validated, no null issues)
- Corrected data delivered to client
- Issue log documented in Jira ticket comments (root cause, fix applied, version if applicable)

---

## Additional Context
- Slack thread: <link to Slack thread, if posted>
- Billing Code: <billing_code input value>
- Start Date: <today's date>
- Due Date: <Friday of the same week>
```

---

### Date Fields
| Field | Value |
|---|---|
| **Start Date** | Today (the date the issue was detected) |
| **Due Date** | Friday of the same week |

---

### Labels
Use account-specific labels from config. Standard format: `<client-shortname>`, `<account-shortname>`, `outbound-feed`.
Example: `<client-shortname>`, `<account-shortname>`, `outbound-feed`

---

## Notes on Billing Code
The `billing_code` is a required annual input. It is the internal digit code used by the team to bill
fix/investigation work against the correct client engagement. This is distinct from the account shorthand.

**Format:** A numeric project code (e.g., `12345`). Confirm with DE lead or PM.

Always confirm with the user before creating any ticket. Never auto-populate or infer this value.

---

## Atlassian MCP — Auth Caveat for Scheduled Runs

**OAuth-based Atlassian MCP disconnects after a few hours.** This is a known issue across
workstations and Claude Desktop. For a weekly scheduled task (Monday 9 AM), the OAuth token
will be expired by fire time.

**Required setup for scheduled/headless use:** API token authentication (not OAuth).

```
claude mcp add atlassian https://mcp.atlassian.com/v1/mcp
```

Authenticate with an Atlassian API token.
Generate tokens at: https://id.atlassian.com/manage-profile/security/api-tokens

**SSE deprecation:** The Atlassian SSE endpoint is being retired after June 30, 2026.

---

## API Token Expiry — 365-Day Maximum

Atlassian API tokens have a **maximum lifetime of 365 days** (enforced by Atlassian as of 2025).
Users cannot create tokens that last longer than this.

**How the skill tracks this:**
- During onboarding (Step 0B), the skill records `jira_token_created: <YYYY-MM-DD>` in `user-config.md`
- On every returning-user invocation (Step 0C), the skill calculates token age
- **At 335+ days (30-day warning window):** Display a warning:
  "⚠️ Your Atlassian API token was created on <date> and expires within 30 days.
  Rotate it at: https://id.atlassian.com/manage-profile/security/api-tokens
  Then re-authenticate: `claude mcp add atlassian https://mcp.atlassian.com/v1/mcp`"
- **After token rotation:** User says "I rotated my Jira token" → skill updates `jira_token_created` to today

**If the user doesn't know when the token was created:** Set `jira_token_created: "unknown"`.
The skill will not warn about expiry but WILL handle auth failures gracefully at runtime.

---

## Runtime Auth Failure Handling

**If Atlassian MCP auth fails at runtime:**
- Log the error in chat
- Do NOT block the Slack alert — still post it
- Tell the user: "Jira ticket creation failed (likely expired token). Slack alert was posted.
  Rotate your token at: https://id.atlassian.com/manage-profile/security/api-tokens
  Then re-authenticate: `claude mcp add atlassian https://mcp.atlassian.com/v1/mcp`"

**Fallback option:** If Atlassian MCP proves unreliable, use the Atlassian CLI (acli) with
API token auth — requires one-time authentication at setup and is fully headless-compatible.
