# Installation Guide — Outbound Feed Monitor

This guide walks you through installing the Outbound Feed Monitor skill in Claude Code.
Once set up, the skill automatically checks your client outbound feed emails on a configurable
schedule, creates Jira tickets for failures, and posts alerts to Slack.

**No Python setup required. No API keys. No OAuth credentials.**
The skill runs entirely through Claude Code connectors.

---

## Required Connectors

You need four connectors active in Claude Code before running the skill:

| Connector | Purpose | How to add |
|---|---|---|
| **Gmail** | Search for feed report emails | Claude Code Settings → Connections → Gmail |
| **Claude browser extension** | Read full email body content (Gmail MCP returns snippets only) | Install from Chrome Web Store: search "Claude browser companion" |
| **Slack** | Post alerts to channel or DM | Claude Code Settings → Connections → Slack |
| **Atlassian (Jira)** | Create tickets on the DT board | `claude mcp add atlassian https://mcp.atlassian.com/v1/mcp` — authenticate with an API token (not OAuth — more reliable for scheduled runs). Generate at: https://id.atlassian.com/manage-profile/security/api-tokens |

> **Jira is optional at setup.** You can skip it during onboarding and enable it later.

---

## Step 1: Install the Skill

Clone the repo and copy the `skill/` folder to your Claude Code skills location:

**Windows:**
```bash
git clone https://github.com/flyshadow-glitch/outbound-feed-monitor.git
xcopy /E /I "outbound-feed-monitor\skill" "%APPDATA%\Claude\skills\outbound-feed-monitor"
```

**Mac/Linux:**
```bash
git clone https://github.com/flyshadow-glitch/outbound-feed-monitor.git
cp -r outbound-feed-monitor/skill ~/.claude/skills/outbound-feed-monitor
```

Restart Claude Code to pick up the new skill.

---

## Step 2: Run the Onboarding Flow

In Claude Code, type:

```
/outbound-feed-monitor
```

The skill detects this is your first run and walks you through setup. It asks 4 questions:

| Step | What happens | Your input |
|---|---|---|
| Connector check | Auto-tests Gmail, Chrome, Slack, Jira | Nothing — automatic |
| **Q1:** Email subject | You provide the subject line; skill searches Gmail and auto-detects account name, feed types, sender, cadence, email count | `Client - Account: Outbound Feed Report` |
| **Q2:** Alert target | Slack channel or DM to you | `#your-alert-channel` or "DM me" |
| **Q3:** Jira config | Project key + billing code (skill auto-finds epics on the DT board) | `DT` / `12345` |
| **Q4:** Schedule | Day and time for automatic runs | `Monday 11 AM` |

The skill saves your config in `references/account-configs.md` and `references/user-config.md`.

---

## Step 3: Verify Your Setup

After onboarding, run a manual check:

```
/outbound-feed-monitor account:your_account
```

The skill will:
1. Search your Gmail for today's feed report emails
2. Open each email in Chrome and parse the feed status table
3. Classify each row (FAILURE / WARNING / INFO / ALL CLEAR)
4. If failures found: create a Jira ticket and post to Slack
5. If no failures: DM you confirming all clear

---

## What Happens on a Scheduled Run

Once scheduled, the skill runs automatically at your configured day and time:

- **Failures detected** — creates a consolidated Jira ticket under the correct epic (PLD or Non-PLD), posts a Slack message with a thread reply linking the ticket
- **No failures** — sends you a private Slack DM. No channel noise.
- **Chrome not running** — sends you a DM to run the check manually

### Jira Ticket Details

Tickets are created with:
- **Project:** DT (Data Team board)
- **Issue type:** Data Issue
- **Epic:** Auto-matched based on your account + brand + PLD/Non-PLD
- **Labels:** client shortname, account shortname, `outbound-feed`
- **Start date:** Day of detection
- **Due date:** Friday of the same week
- **Original estimate:** 4h (single feed), 6h (2-3 feeds), 8h (4+ feeds)
- **Assignee:** Unassigned — DE lead triages from the board

### Slack Alert Format

```
:thread1: Non-PLD | <client> | <brand> | DCM
    └── https://<instance>.atlassian.net/browse/DT-XXXX
```

---

## Adding More Accounts

To monitor additional client accounts:

```
/outbound-feed-monitor add
```

The skill asks for the new account's email subject line, auto-detects feed types from a sample email,
then lets you configure Slack, Jira, and scheduling. Each account gets its own schedule and config.

---

## Lifecycle Commands

| Command | What it does |
|---|---|
| `/outbound-feed-monitor` | Run feed check (onboards if first time) |
| `/outbound-feed-monitor account:<name>` | Run check for a specific account |
| `/outbound-feed-monitor setup` | Configure only — no check |
| `/outbound-feed-monitor reset` | Clear all config and restart onboarding |
| `/outbound-feed-monitor add` | Add a new account |
| `/outbound-feed-monitor status` | Show configured accounts and schedules |
| `/outbound-feed-monitor pause [account]` | Disable scheduled task |
| `/outbound-feed-monitor resume [account]` | Re-enable scheduled task |
| `/outbound-feed-monitor remove <account>` | Remove account from monitoring |
| `/outbound-feed-monitor uninstall` | Show cleanup steps |

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Jira MCP connector disconnected | Re-authenticate in Claude Code settings. API tokens expire after 365 days max. |
| No emails found | Verify the sender email and subject line in your account config. Check Gmail has access to the feed report emails. |
| Wrong epic matched | Re-run onboarding and correct the brand or client name. The skill searches epics by `<Client> - <Brand> - [Non PLD/PLD] - Maintenance`. |
| Skill not found after install | Restart Claude Code. Check the skill directory is in the correct location. |
| Scheduled task DMs instead of posting | Chrome was not running when the task fired. Ensure Chrome is open with the Claude extension active on scheduled run days. |

---

## Questions?

Open an issue on this repo or reach out to the Analytics & Strategy team.
