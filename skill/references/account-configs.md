# Account Config Profiles — Outbound Feed Monitor

This file stores account configurations created during onboarding. It ships **empty** —
every account is user-defined via the setup flow (SKILL.md Step 0D).

When the skill loads, it reads the matching config to determine what to search for,
how many emails to expect, how to classify feed types, and where to route alerts.

---

<!-- Account configs are added automatically during onboarding (SKILL.md Step 0D). -->
<!-- Each config block is created by analyzing a sample feed report email. -->

## Config: Abbott ADC (`account:adc`)

```
account_name:         Abbott ADC
account_shortname:    adc
client_shortname:     abbott
brand:                FreeStyle Libre

email_subject:        Abbott - ADC: Outbound Feed Report
sender_email:         analytics-de+airflow@klickcloud.net
cadence_day:          Monday
expected_email_count: 3   # Media (~14:05 UTC), PLD (~14:10), SEO (~14:35); Gmail may group them in one thread

feed_types:
  - name: Media (Non-PLD)
    stream: Non-PLD
    file_patterns:  [_GA_, _BING_, _DCM_, _DAYPART_]
    table_patterns: [google_ads, bing_ads, dcm, daypart]
    notes: GA + Bing run through Stitch; DCM through custom Klick APIs.
  - name: PLD
    stream: PLD
    file_patterns:  [_PLD_]
    table_patterns: [pld]
  - name: SEO
    stream: Non-PLD
    file_patterns:  [_GSC_]
    table_patterns: [gsc]

known_exceptions:
  - source_table: medscape_pld_abbott_adc
    condition:    Failed OR 0 rows
    severity:     INFO
    reason:       Medscape PLD produces 0 rows in weeks with no active Medscape campaign.
    action_note:  Confirm Medscape was inactive this week. If it was active, escalate as a real failure.

client_email:
  enabled:        true
  signoff_name:   Edison

slack:
  production_channel_id: C02U1NTHUK1
  production_channel:    "#dataeng-support"
  test_user_id:          U059RTH6ZFC
  thread_header:         ":thread1: ADC Outbound Issues:"

jira:
  production_project_key: DT
  cloud_id:               dc266482-5597-4418-a075-890d22d0caf6
  instance:               klickanalytics.atlassian.net
  issue_type:             Task
  labels:                 [abbott, adc, outbound-feed]
```

---

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
cst_option_id:        [Jira select option ID for CST — resolved during onboarding via getJiraIssueTypeMetaWithFields]
client:               [Client name — must match Jira dropdown exactly]
client_option_id:     [Jira select option ID for Client — resolved during onboarding via getJiraIssueTypeMetaWithFields]
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

client_email:
  enabled:                true            # reply-all to the client on Failed rows (SKILL.md Step 4B)
  signoff_name:           [Name to sign client emails with, e.g. "Edison"]

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
