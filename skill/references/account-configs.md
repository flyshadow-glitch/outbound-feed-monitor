# Account Config Profiles — Outbound Feed Monitor

This file stores account configurations created during onboarding. It ships **empty** —
every account is user-defined via the setup flow (SKILL.md Step 0D).

When the skill loads, it reads the matching config to determine what to search for,
how many emails to expect, how to classify feed types, and where to route alerts.

---

<!-- Account configs are added automatically during onboarding (SKILL.md Step 0D). -->
<!-- Each config block is created by analyzing a sample feed report email. -->

## Template — New Account

The skill uses this template when writing a new account config. Do not remove it.

```
account_name:         [Full client + account name]
account_shortname:    [Short trigger keyword, e.g. "acme"]
client_shortname:     [Client name for labels, e.g. "acme"]
brand:                [Brand name, e.g. "BrandX"]

email_subject:        [Exact subject line to search in Gmail]
sender_email:         [Airflow or pipeline sender email]
cadence_day:          [Monday / Tuesday / etc.]
expected_email_count: [How many emails expected per cadence run]

# Jira required fields — collected during onboarding
cst:                  [Team name — select from your organization's team list]
client:               [Client name — must match Jira dropdown exactly]
billing_code_nonpld:  [Annual project code for Non-PLD maintenance — confirm with DE lead/PM, or "TBD"]
billing_code_pld:     [Annual project code for PLD maintenance — confirm with DE lead/PM, or "TBD"]

# Epic mapping — searched on DT board during onboarding
# Pattern: "<Client> - <Brand> - Non PLD - Maintenance" and "<Client> - <Brand> - PLD Maintenance"
# Use JQL: project = DT AND issuetype = Epic AND summary ~ "<Client>" AND summary ~ "<Brand>"
epics:
  nonpld_key:         [e.g. DT-XXXX]
  nonpld_summary:     [e.g. "<Client> - <Brand> - Non PLD - Maintenance"]
  pld_key:            [e.g. DT-XXXX]
  pld_summary:        [e.g. "<Client> - <Brand> - PLD Maintenance"]

feed_types:
  - name:             [Feed type display name]
    stream:           [PLD or Non-PLD]
    file_patterns:    [List of substrings that identify this feed type in file names]
    table_patterns:   [List of substrings in source table names]
    channel_labels:   [Map of table pattern → display label for Slack, e.g. dcm: "DCM"]
    notes:            [Any pipeline-specific context]

known_exceptions:
  - source_table:     [Exact source table name]
    condition:        [e.g., "Status = Failed OR Number of Rows = 0"]
    severity:         INFO
    reason:           [Why this is expected]
    action_note:      [What the user should verify manually]

slack:
  production_channel_id:  [Channel ID — resolve via slack_search_channels during setup]
  production_channel:     [#channel-name]
  test_user_id:           [User's Slack ID for DMs]

jira:
  production_project_key: DT
  test_project_key:       [e.g., TEST — user's own board for testing]
  cloud_id:               [your Jira cloud ID]
  instance:               [your-instance.atlassian.net]
  issue_type:             Data Issue
  issue_type_id:          "10019"
  issue_source:           Media Vendor
  issue_source_option_id: "11249"
  labels:                 [client-shortname, account-shortname, outbound-feed]
  default_priority:       Medium

estimate:
  single_feed:            "4h"
  two_to_three_feeds:     "6h"
  four_plus_feeds:        "8h"
```

## Onboarding Flow

Onboarding is handled by SKILL.md Steps 0A–0D. The skill asks 4 questions (email subject,
Slack target, Jira config, schedule), then auto-detects everything else from a sample email.
See SKILL.md for the full onboarding spec — do not duplicate the question list here.

## Jira Custom Field Reference

| Field | Key | Type | Required |
|---|---|---|---|
| CST | customfield_10036 | Select (option value) | Yes |
| Client Information | customfield_10037 | Select (option value) | Yes |
| Project Code | customfield_10038 | Text | Yes |
| Issue Source | customfield_10045 | Select (option value) | Yes |
| Start date | customfield_10015 | Date (YYYY-MM-DD) | No |
| Expected Delivery Date | customfield_10535 | Date (YYYY-MM-DD) | No |
| Requestor | customfield_10044 | Text | No |
| Genome Task # | customfield_10041 | Text | No |
| Github Repository | customfield_10042 | Text | No |

## Slack Message Format

**When issues found** — post to production channel:
- Main message: `:thread1: <stream> | <client> | <brand> | <channel or "multiple">`
- Thread reply: Jira ticket link

**When no issues** — DM user only:
- "No issues identified from today's outbound feed from <account>."
