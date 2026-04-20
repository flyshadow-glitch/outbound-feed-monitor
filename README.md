# outbound-feed-monitor

Monitors client outbound feed pipeline emails and alerts the team on failures —
automatically creating Jira tickets on the DT board and posting alerts to Slack.

**No Python setup required. No OAuth credentials. No API keys.**
The skill runs entirely through Claude Code connectors.

---

## Quick Start

See **[INSTALL.md](INSTALL.md)** for the full guide.

```
/outbound-feed-monitor
```

The skill walks you through setup in ~5 minutes and runs automatically on your chosen schedule.

---

## Required Connectors

| Connector | Purpose |
|---|---|
| **Gmail** | Search for feed report emails |
| **Claude browser extension** | Read full email body content |
| **Slack** | Post alerts to channel or DM |
| **Atlassian (Jira)** | Create tickets on the DT board (optional) |

> The Gmail MCP `get_thread` tool does not return email body content (confirmed bug, April 2026).
> The skill reads email bodies by navigating Chrome to each Gmail thread URL.

---

## How It Works

1. **Search** — Gmail MCP finds today's feed report emails by subject + sender
2. **Read** — Chrome browser opens each email and reads the full body via `get_page_text`
3. **Classify** — each row is classified FAILURE / WARNING / INFO / ALL CLEAR
4. **Alert** — Slack message posted to channel; Jira ticket created on DT board
5. **All clear** — private DM to you only, no channel noise

---

## Classification Logic

Each row in the email body is classified in this order (first match wins):

| Condition | Result |
|---|---|
| `source_table` matches a `known_exceptions` entry | ℹ️ INFO |
| `status == "Failed"` | 🔴 FAILURE |
| `status == "Exported"` and `row_count == 0` | 🟡 WARNING |
| `status == "Exported"` and null columns present | 🟡 WARNING |
| `status == "Exported"` and `row_count > 0` | ✅ ALL CLEAR |
| Expected email not received | 🔴 FAILURE (account level) |

The overall account status is the worst severity across all rows.

---

## Adding a New Account

Run `/outbound-feed-monitor add` — the skill asks for the email subject line and auto-detects
everything else from a sample email (sender, cadence day, feed types, expected email count).

Or add a block manually to `config/accounts.yaml`:

```yaml
accounts:
  myaccount:
    account_name: "Client - Account Name"
    brand: "Brand Name"
    email_subject: "Client - Account: Outbound Feed Report"
    sender_email: "pipeline-sender@example.net"
    cadence_day: Monday
    expected_email_count: 3

    feed_types:
      - name: "Non-PLD"
        stream: "Non-PLD"
        file_patterns: ["_GA_", "_BING_", "_DCM_"]
        table_patterns: ["google_ads", "bing_ads", "dcm"]
        channel_labels:
          dcm: "DCM"
          google_ads: "GA"
          bing_ads: "Bing"

    known_exceptions: []

    slack:
      production_channel_id: CXXXXXXXXXX
      production_channel: "#your-alert-channel"
      test_user_id: UXXXXXXXXXX

    jira:
      production_project_key: DT
      cloud_id: "<your-cloud-id>"
      instance: "<your-instance>.atlassian.net"
      labels: ["client-shortname", "account-shortname", "outbound-feed"]
```

No code changes needed — feed types, patterns, and known exceptions are all config-driven.

---

## Project Structure

```
outbound-feed-monitor/
├── README.md
├── INSTALL.md                ← Skill installation + onboarding guide
├── config/
│   ├── accounts.example.yaml ← template — copy to accounts.yaml
│   └── accounts.yaml         ← your account config (gitignored)
├── skill/                    ← Claude Code skill files
│   ├── SKILL.md              ← Main skill definition (8-step workflow)
│   └── references/
│       ├── account-configs.md    ← Account profile template + Jira field reference
│       ├── feed-types.md         ← Feed classification rules
│       ├── jira-template.md      ← Jira ticket description template
│       ├── slack-template.md     ← Slack message format spec
│       └── user-config.md        ← Per-user config (populated during onboarding)
└── core/                     ← Python CLI (debugging only — not required for skill)
    ├── gmail_reader.py
    ├── feed_classifier.py
    ├── slack_alerter.py
    └── jira_manager.py
```

---

## Status

| Feature | Status |
|---|---|
| Gmail search + Chrome body reading + classification | Done |
| Claude Skill — onboarding flow | Done |
| Claude Skill — Jira ticket creation (DT board, full field mapping) | Done |
| Claude Skill — Slack alerts (channel + thread reply) | Done |
| Claude Skill — scheduled runs (day/time configurable) | Done |
| Python CLI (debugging / offline classification) | Done |
| Multi-account simultaneous monitoring | Planned |
| Billing code auto-sync with Genome | Planned |

---

## Troubleshooting

| Issue | Fix |
|---|---|
| No emails found | Verify the sender email and subject line in your account config. Check Gmail MCP is connected. |
| Email body not parsed | Ensure Chrome is open with the Claude browser extension active. |
| Scheduled task DMs instead of alerting | Chrome was not running when the task fired. Open Chrome with the extension before the scheduled run time. |
| Jira MCP disconnected | Re-authenticate in Claude Code settings. API tokens expire after 365 days max. |
| Wrong epic matched | Re-run onboarding and correct the brand or client name. The skill searches epics by `<Client> - <Brand> - [Non PLD/PLD] - Maintenance`. |
| Skill not found after install | Restart Claude Code. Check the skill directory is in the correct location. |
