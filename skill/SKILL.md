---
name: outbound-feed-monitor
description: >
  Monitors client outbound feed emails on a scheduled cadence and alerts on failures or missing emails.
  Use this skill when the user says '/outbound-feed-monitor', 'check [account] feeds', 'run the feed check',
  'did the outbound feeds run', '[account] outbound status', or any variation asking about outbound feed
  report emails for any client account. Also trigger for 'did all feed emails arrive', 'any feed failures
  today', 'check <account> feeds', 'set up feed monitoring', 'schedule feed check',
  or similar account-specific feed check and onboarding requests.
---

# Outbound Feed Monitor

A self-service skill for monitoring client outbound feed pipeline emails. Any analyst or DE team member
can install this skill, configure their accounts and alert targets, and run checks on-demand or on a
Monday morning schedule.

**Trigger command:** `/outbound-feed-monitor account:<name>` or any phrase matching the description above.

---

## First Run — Onboarding

On first invocation, check if the user has been onboarded by looking for a user config section
in `references/user-config.md`. If no config exists for the current user, run the onboarding flow.

### Step 0A — Check MCP Connectors

Before asking any setup questions, verify the required MCP connectors are available.
Test each by calling a lightweight read-only operation:

| Connector | Test call | Required? |
|---|---|---|
| **Gmail** | `search_threads` with `query: "newer_than:1d" pageSize: 1` | Yes — skill cannot function without it |
| **Slack** | `slack_search_users` with the user's name | Yes for alerts |
| **Jira/Atlassian** | `getAccessibleAtlassianResources` | Optional — can defer Jira to later |

**If Gmail is missing:** Stop. Tell the user:
"This skill requires the Gmail MCP connector. In Claude Code, go to Settings → MCP Servers and add
the Gmail connector. Once connected, run this skill again."

**CLI availability check:** After MCP checks, verify the Python CLI is installed by running:
```bash
outbound-feed-monitor --help
```
- If the command succeeds: auto-set `cli_path = outbound-feed-monitor`. No question needed.
- If the command fails: tell the user:
  "The Python CLI is not installed. Run `pip install -e .` from your cloned repo directory,
  then come back. See INSTALL.md for details."
  Also ask: "What's the absolute path to your cloned repo?" → save as `config_dir`.

**Gmail body retrieval note:** The Gmail MCP's `get_thread FULL_CONTENT` does NOT return email body
content (confirmed bug as of April 2026 — the tool returns headers and snippet only). The skill uses
the Python CLI (`monitor.py --json`) as the primary path for email body reading. Chrome browser is the
interactive fallback. Do NOT attempt to use `get_thread` for body parsing.

**If Slack is missing:** Warn but continue:
"Slack connector not found. I can still check feeds and display results, but I won't be able to post
alerts. Add the Slack MCP connector when you're ready."

**If Jira/Atlassian is missing:** Note it and continue:
"Atlassian MCP not detected. Jira ticket creation will be skipped. To enable it later, run:
`claude mcp add atlassian https://mcp.atlassian.com/v1/mcp`
and authenticate with your Atlassian API token (not OAuth — API tokens are more reliable for
scheduled/headless runs). Note: Atlassian API tokens expire after a maximum of 365 days.
Generate tokens at: https://id.atlassian.com/manage-profile/security/api-tokens"

### Step 0B — Capture User Config & Define First Account

This plugin ships with NO pre-configured accounts. Every account is user-defined.
The onboarding is designed to be fast — 4 questions max. Everything else is auto-detected.

**Auto-detected (no questions needed):**
- **Gmail address:** read from the Gmail MCP profile or the first search result headers
- **Account name, sender, feed types, expected email count:** all auto-detected from the sample email (Step 0D)
- **Cadence day:** inferred from the date of the sample emails
- **Jira labels:** auto-generated as `[<client-shortname>, <account-shortname>, outbound-feed]`

**Deferred (asked later when needed, not during onboarding):**
- **Known exceptions:** skip at setup. If a table repeatedly shows 0 rows or Failed, the skill
  will notice the pattern and ask: "This table has failed 2 weeks in a row. Is this a known exception?"
  User can also add exceptions anytime with "add exception for [table]".

**Ask these 4 questions ONE AT A TIME:**

1. **"What's the email subject line for the feed report you want to monitor?"**
   - User provides the exact subject line (e.g., "Client - Account: Outbound Feed Report")
   - Search Gmail for recent emails matching that subject → auto-detect account config (Step 0D)
   - Present findings for confirmation: feed types, email count, sender

2. **"Where should alerts go? A Slack channel or DM to you?"**
   - If channel: ask for the channel name, search Slack to resolve the ID
   - If DM or unsure: default to DM. "I'll DM you while we test. Switch to a channel anytime."

3. **"What Jira project key and billing code should I use for tickets?"** (only if Atlassian MCP is available)
   - User provides project key (e.g., DT) and billing code (e.g., 25000)
   - Or: "Skip Jira for now" — skill will still post Slack alerts without tickets

4. **"Want this to run automatically? If so, what day and time?"**
   - User picks day + time (e.g., "Monday 11 AM")
   - Or: "No, I'll run it manually" — user can schedule later with "schedule feed check"

Save the user config to **both** locations (session cache + stable path):
- Session cache: `references/user-config.md` (fast access, lost between sessions)
- Stable path: `<config_dir>/user-config.md` (persists across sessions — canonical source of truth)

`config_dir` is set during onboarding to the directory where the Python CLI is installed
(e.g., `C:/Working/outbound-feed-monitor`). All subsequent reads check the stable path first.

```
## User: <username>

gmail: <email>
accounts: [<account_shortname>]
slack_target: <user_id or channel_id>
slack_mode: dm | channel
jira_enabled: true | false
jira_project_key: <key>
jira_token_created: <YYYY-MM-DD or "unknown">
billing_code_nonpld: <code or "TBD">
billing_code_pld: <code or "TBD">
cst: <CST team name>
config_dir: <absolute path to the CLI installation directory>
cli_path: outbound-feed-monitor
scheduled: true | false
schedule_cron: <cron expression>
```

**One-time fields (never re-asked after onboarding):** `slack_target`, `slack_mode`,
`billing_code_nonpld`, `billing_code_pld`, `cst`, `jira_project_key`, `config_dir`, `cli_path`,
`schedule_cron`. Only surface these again if the user says "reconfigure" or "update billing codes".

### Step 0C — Skip Onboarding for Returning Users

On every invocation, check for existing config in this order:
1. **Stable path first:** `<config_dir>/user-config.md` — if `config_dir` is known from a previous session
2. **Session cache:** `references/user-config.md` — fast access within the same session

If a config is found in either location, load it silently and copy to both locations if one is missing.
Only ask for inputs that are missing or if the user explicitly says "reconfigure" or "change settings".

**Jira token expiry check:** If `jira_enabled = true` and `jira_token_created` is set,
calculate the age of the token. If older than 335 days (30-day warning window before 365-day max):
"⚠️ Your Atlassian API token was created on <date> and expires within 30 days.
Rotate it at: https://id.atlassian.com/manage-profile/security/api-tokens
Then re-authenticate: `claude mcp add atlassian https://mcp.atlassian.com/v1/mcp`"

### Step 0D — Account Definition from Sample Email

This is the **primary** path for adding any account — including the very first one.
No accounts are pre-configured. Every account is built from a sample email.
This step is triggered by Step 0B question 1 (the user provides the email subject line).

1. Search Gmail for recent emails matching the subject:
   ```
   q: subject:"<subject line>" maxResults: 20
   ```
2. Read 1–2 email bodies and auto-detect:
   - **Account name:** derived from the subject line (e.g., "Client - Account" → account_name: "Client Account", shortname: "account")
   - **Sender email:** from the email headers
   - **Cadence day:** inferred from the day-of-week the emails were sent
   - **Feed types** based on file name patterns (group by common prefixes)
   - **Expected email count:** how many distinct emails match that subject on the same day
   - **Source table names**
   - **Jira labels:** auto-generate as `[<client-shortname>, <account-shortname>, outbound-feed]`
3. Present findings for confirmation in a single summary:
   "Here's what I detected from your feed emails:
   - Account: [name] (shortname: [shortname])
   - Sender: [email]
   - Cadence: [day], [N] emails per run
   - Feed types: [list with file counts]
   Does this look right?"
4. If confirmed: write the config block to `references/account-configs.md`
5. Add the account shortname to the user's `accounts` list in `references/user-config.md`
6. Continue to Step 0B questions 2–4 (Slack, Jira, schedule)

**Known exceptions are NOT asked during onboarding.** They are added later:
- Automatically: if a table fails 2+ consecutive weeks, the skill asks "Is this expected?"
- Manually: user says "add exception for [table]" at any time

**Adding additional accounts later:** When a user already has a config and says
"add account <name>" or runs the skill with an unknown account name, jump directly to Step 0D
then ask only questions 2–4 from Step 0B (Slack, Jira, schedule) — reuse existing values as defaults.

---

## Step 1 — Resolve Account Config

**If the account name is provided** (e.g., `account:<shortname>`):
Load the matching config from `references/account-configs.md`.

**If no account is specified:**
Ask: "Which account should I check? Your configured accounts: [list from user-config.md]"

Load config silently. Do NOT prompt the user for any config values on a recurring run.
All required values (`billing_code`, `slack_target`, `jira_project_key`) are read from the saved config.

If a required value is missing from config (e.g., first run incomplete), ask for it once and save it.

Never proceed to Step 2 without a resolved account config.

---

## Step 2 — Search Gmail for Feed Emails

Using values from the account config, call `search_threads`:
```
query: subject:"<config.email_subject>" from:<config.sender_email> after:<target date YYYY/MM/DD>
pageSize: 20
```

**Target date logic:**
- Default: today's date
- If user specifies a date: use that date
- If today is NOT the configured cadence day: inform the user and offer to check the most
  recent cadence day instead. Do not abort — let the user decide.

**Expected result:** `config.expected_email_count` emails. Capture all message IDs.

- If fewer emails than expected are found, flag which feed type(s) are missing (determined in Step 3).
- If 0 emails found: post a **no-email alert** to the user's Slack target using `config.no_email_alert`
  (or default: "No feed report emails found. Check the outbound pipeline — emails may not have been sent.")
  This is a 🔴 FAILURE at the account level. Proceed to Step 5 (Slack alert) and Step 6 (Jira) if enabled.
  Do NOT proceed to Steps 3–4 (there are no emails to parse).

---

## Step 3 — Read and Parse Each Email

**⚠️ Do NOT use `get_thread FULL_CONTENT` for body reading.** The Gmail MCP returns headers and
snippet only — no body content. This is a confirmed bug in the connector (April 2026).

### Primary path — Python CLI (headless-safe, works offline/scheduled)

If `cli_path` is set in user config, run from `config_dir`:
```bash
cd <config_dir> && <cli_path> --account <account_shortname> --json
```

Parse the JSON output. The JSON schema:
```json
{
  "account": "<Account Name>",
  "account_shortname": "<shortname>",
  "date": "YYYY-MM-DD",
  "overall_severity": "FAILURE | WARNING | INFO | ALL_CLEAR",
  "emails_found": 3,
  "emails_expected": 3,
  "feed_summaries": [
    { "name": "DCM", "severity": "FAILURE", "file_count": 2,
      "problem_tables": ["<client>_hcp_dcm"], "info_tables": [] }
  ],
  "problem_rows": [
    { "file_name": "...", "status": "Failed", "source_table": "...",
      "report_from": "YYYY-MM-DD", "report_to": "YYYY-MM-DD",
      "row_count": 0, "null_columns": "", "feed_type": "DCM",
      "severity": "FAILURE", "exception_reason": null }
  ]
}
```

Use `overall_severity` and `problem_rows` to drive Steps 4–6. Skip Steps 3 HTML parsing —
the CLI handles all of that.

**If the CLI returns a non-zero exit code:** Log the error in chat, fall back to Chrome path below.

### Fallback path — Chrome browser (interactive sessions only)

If `cli_path` is not set or CLI fails, and Chrome with the Claude extension is available:
1. Navigate to Gmail in Chrome and open the email thread
2. Use `get_page_text` to extract the full email body text
3. Parse the text table manually using the field order:
   File Name | Status | Source Table | Report From | Report To | Number of Rows | Null Columns

Skip non-data rows:
- Lines matching "Publisher Counts:" header — skip
- Indented publisher breakdown lines (individual publisher names) — skip

**If Chrome is not available and CLI is not set:** Block. Tell the user:
"Email body cannot be read without either the Python CLI or the Chrome extension.
To fix: set `cli_path` in your config pointing to monitor.py, or open Chrome with the Claude extension."

---

## Step 4 — Classify Results

**Classification decision table (evaluate top-to-bottom, first match wins):**

| Condition | Result |
|---|---|
| `source_table` matches a `known_exceptions` entry AND condition matches | ℹ️ INFO |
| `status == "Failed"` | 🔴 FAILURE |
| `status == "Exported"` AND `row_count == 0` | 🟡 WARNING |
| `status == "Exported"` AND `null_columns` is NOT `N/A` or `[]` | 🟡 WARNING |
| `status == "Exported"` AND `row_count > 0` | ✅ ALL CLEAR |
| Expected email not received (fewer than `expected_email_count`) | 🔴 FAILURE (account-level) |

**Known exception condition values:**
- `"Failed"` — matches when status == "Failed"
- `"0 rows"` — matches when row_count == 0
- `"Failed OR 0 rows"` — matches either condition

**For known exceptions with an `action_note`:**
Display the action_note to the user. Example: "Confirm with the client whether the campaign source
was active that week. If active, escalate — this is a real failure, not an exception."

**Overall account severity** = worst severity across all rows + email count check.
If ALL CLEAR: post confirmation and stop. No Jira.
If INFO only: post INFO note. No Jira.
If WARNING or FAILURE: proceed to Steps 5 and 6.

---

## Step 5 — Post Slack Alert

Load `references/slack-template.md` for message format and emoji conventions.

**DM mode (testing — `notify_target` is a user ID):**
Send a single DM using `slack_send_message` with `channel_id` = user ID. No thread needed.

**Channel mode (production — `notify_target` is a channel ID):**
1. Post parent message (thread header from config)
   using `slack_send_message`
2. Capture the returned message `ts` from the response
3. Post detail as a thread reply using `slack_send_message` with `thread_ts` set to parent `ts`

**Channel mode message format (from slack-template.md):**
- Message 1 (parent): `:thread1: <stream> | <client> | <brand> | <affected feed types>`
- Message 2 (thread reply): `Ticket: <JIRA_LINK>` — posted after Step 6

All failure detail goes in the Jira ticket description. Do not add detail to the Slack thread.

**ALL CLEAR mode:** If configured to send all-clear messages, DM the user only — never post to channel.

---

## Step 6 — Create Jira Ticket (if `jira_enabled = true`)

### 6A — Check for Atlassian MCP

Look for Atlassian MCP tools (e.g., `createJiraIssue`, `getAccessibleAtlassianResources`).
If not available, skip Jira and tell the user:
"Jira MCP not available — skipping ticket creation. To enable: `claude mcp add atlassian https://mcp.atlassian.com/v1/mcp`"

### 6B — Deduplication Check

Before creating a ticket, search for an existing open ticket from this week:
- Search Jira for issues in the project with summary containing `[<ACCOUNT> Outbound] Feed Export Failure`
- Filter to issues created within the current ISO week
- Filter to open/in-progress status

**If existing ticket found:** Add a comment to the existing ticket with:
- What's still failing
- What's new since last check
- What has been resolved
- Tell the user: "Found existing ticket [KEY-XXX] — added comment instead of creating duplicate."

**If no existing ticket found:** Create new ticket.

### 6C — Create Ticket

Use `createJiraIssue` with `contentFormat: "markdown"` and `additional_fields` (not `additionalFields`):

```
createJiraIssue(
  cloudId: <account_config.jira.cloud_id>,
  projectKey: <user_config.jira_project_key>,   # e.g. "DT"
  issueTypeName: "Data Issue",
  summary: "[<ACCOUNT> Outbound] Feed Export Failure — <YYYY-MM-DD>",
  contentFormat: "markdown",
  description: <filled from references/jira-template.md>,
  additional_fields: {
    "customfield_10036": {"id": "<cst_option_id>"},        # CST
    "customfield_10037": {"id": "<client_option_id>"},     # Client Information
    "customfield_10038": "<billing_code>",                 # Project Code (text)
    "customfield_10045": {"id": "11249"},                  # Issue Source: Media Vendor
    "customfield_10015": "<today YYYY-MM-DD>",             # Start date
    "customfield_10535": "<friday YYYY-MM-DD>",            # Expected Delivery Date
    "parent": {"key": "<epic_key>"},                       # Non-PLD or PLD epic from config
    "labels": ["<client-shortname>", "<account-shortname>", "outbound-feed"],
    "priority": {"name": "Medium"}
  }
)
```

**CST and Client option IDs** are stored in account-configs.md after first lookup.
If not cached, call `getJiraIssueTypeMetaWithFields` with `projectIdOrKey: "DT"` and `issueTypeId: "10019"`
to find them, then save to config.

After ticket is created, post the Jira link as a thread reply on the Slack parent message.

### 6D — Jira Not Available Fallback

If Atlassian MCP fails at runtime (auth expired, network error):
- Log the error in chat: "Jira ticket creation failed: [error]. Slack alert was still posted."
- Do NOT retry or block the rest of the workflow.
- Complete the Slack alert and user summary normally.

---

## Step 7 — Schedule (if requested)

When the user opts into scheduling during onboarding or says "schedule this":

Use `create_scheduled_task` with:
- **taskId:** `feed-check-<account_shortname>`
- **cronExpression:** `"0 9 * * 1"` (Monday 9 AM local time, adjustable)
- **prompt:** A complete prompt that runs the feed check:

```
Run the outbound feed monitor for account:<ACCOUNT>.
Config dir: <config_dir>
CLI path: <cli_path>

1. Load config from <config_dir>/user-config.md and <config_dir>/account-configs.md.
2. Run: cd <config_dir> && <cli_path> --account <account_shortname> --json
   Parse the JSON output to get overall_severity and problem_rows.
3. If FAILURE or WARNING:
   - Post Slack alert to <notify_target> (channel_id: <slack_channel_id>)
     Parent: ":thread1: <stream> | <client> | <brand> | <affected feeds>"
   - Create Jira ticket in project <jira_project_key>
     Use billing code: <billing_code_nonpld or billing_code_pld depending on stream>
     Post ticket link as thread reply on Slack parent.
4. If ALL CLEAR or INFO only: DM <user_slack_id> with confirmation.
5. Post summary to chat.
```

Tell the user: "Scheduled! Feed check will run every Monday at 9:00 AM ET.
You can also run it anytime with '/check-outbound-feeds account:<name>'."

---

## Step 8 — Summarize to User

```
✅ Outbound Feed Check Complete — <ACCOUNT>, <DATE>

Emails found: X/<expected>
Failures: [list affected feed types + source tables, or "None"]
Warnings: [list or "None"]
Info: [known exceptions noted with action_note, or "None"]

Slack alert: [channel/DM posted] ✓  (or "skipped — connector not available")
Jira ticket: [KEY-XXX link] ✓  (or "comment added to existing" or "skipped")
Schedule:    [Monday 9 AM ET] ✓  (or "not scheduled")
```

---

## Hard Rules

- Never post to a production channel during testing — use DM until the user explicitly switches.
- Never assume all emails arrived. Always count threads returned by Gmail search.
- Never create a Jira ticket if status is ALL CLEAR or INFO only.
- Never invent row counts, dates, or file names — use only parsed email body values.
- Never create a Jira ticket without a confirmed `billing_code` from config. If TBD, ask once, save, never ask again.
- Never re-ask for billing codes, CST, Slack target, or schedule on a recurring run — load from config silently.
- If Jira creation fails, log the error in chat and still complete the Slack alert.
- Known exceptions are INFO only — do not escalate them to FAILURE or create tickets for them alone.
  But DO surface the `action_note` if one exists (e.g., "Confirm whether the campaign source was active this week").
- When parsing row counts, strip commas before converting to integer (e.g., "3,768" → 3768).
- `Null Columns` values of `N/A`, `[]`, or empty string all mean "no nulls" — do not trigger WARNING.
- Publisher breakdown sub-rows (PLD emails) are display-only — do not classify them as main data rows.
- Never use `get_thread FULL_CONTENT` for email body content — it returns no body (MCP bug). Use CLI or Chrome.
- The Jira MCP parameter for custom fields is `additional_fields` (not `additionalFields`).
- Always write config to both the stable `config_dir` path AND the session `references/` cache.
