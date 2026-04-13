# Installation Guide — Outbound Feed Monitor

This guide walks you through installing and configuring the Outbound Feed Monitor skill in Claude Code. Once set up, the skill automatically checks your client outbound feed emails on a weekly schedule, creates Jira tickets for failures, and posts alerts to Slack.

---

## Prerequisites

1. **Claude Code** installed and running
2. **Python 3.11+** — verify with `python --version`
3. **MCP connectors** enabled for:
   - **Gmail** — to read feed report emails
   - **Slack** — to post alerts and DM summaries
   - **Atlassian (Jira)** — to create tickets (optional — can add later)
4. **Feed report emails** in your Gmail — you need access to the automated pipeline emails
5. **`credentials.json`** for Gmail OAuth — see setup path below

---

## Gmail OAuth Setup (two paths)

The Python CLI reads email bodies directly via the Gmail API (the MCP connector's body retrieval has a known bug). This requires a one-time OAuth setup.

### Path A: You already have `credentials.json` from your team (most users)

Your team admin has already created the Google Cloud project. You just need the shared `credentials.json` file.

1. Get `credentials.json` from your team lead or shared drive
2. Place it in the repo root (after cloning in Step 1)
3. On first CLI run, a browser window opens — sign in with your Google account
4. Done. A `token.json` is saved locally and auto-refreshes. No re-auth needed.

### Path B: You're setting up from scratch (admin / first-time team setup)

Follow the full [Google Cloud Setup guide in README.md](README.md#1-google-cloud-setup-gmail-oauth) to create a project and download `credentials.json`. This takes ~5 minutes and only needs to happen **once per team**. Share the resulting `credentials.json` with your team so they can use Path A.

> **Security note:** `credentials.json` and `token.json` are in `.gitignore`. Never commit them. `credentials.json` is an app credential (safe to share within your team). `token.json` is your personal auth token (do not share).

---

## Step 1: Install the CLI

```bash
pip install git+https://github.com/flyshadow-glitch/outbound-feed-monitor.git
```

This installs the `outbound-feed-monitor` command system-wide. After this, you can call it from anywhere:

```bash
outbound-feed-monitor --account myaccount --json
```

> **For contributors / development:** clone the repo and use `pip install -e .` instead for editable mode.

---

## Step 2: Set Up Your Working Directory

Create a directory for your config files and place `credentials.json` in it:

```bash
mkdir outbound-feed-monitor && cd outbound-feed-monitor
# Place credentials.json here (from Path A or B above)
```

On first CLI run, the browser will open for Google auth. After that, `token.json` is created automatically.

---

## Step 3: Install the Skill

Clone the repo (or just the `skill/` folder) and copy it to your Claude Code skills location:

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

Restart Claude Code (or reload skills) to pick up the new skill.

---

## Step 4: Run the Onboarding Flow

In Claude Code, type:

```
/outbound-feed-monitor
```

The skill will detect this is your first run and walk you through setup. You'll be asked:

| Step | What happens | Your input |
|---|---|---|
| MCP + CLI check | Auto-tests Gmail, Slack, Jira connectors and verifies `outbound-feed-monitor` is on PATH | Nothing — automatic |
| **Q1:** Email subject | You provide the subject line; skill searches Gmail and auto-detects account name, feed types, sender, cadence, email count | `Client - Account: Outbound Feed Report` |
| **Q2:** Alert target | Slack channel or DM to you | `#your-alert-channel` or "DM me" |
| **Q3:** Jira config | Project key + billing code (skill auto-finds epics on the DT board) | `DT` / `12345` |
| **Q4:** Schedule | Day and time for automatic runs | `Monday 11 AM` |

The skill saves your config locally in `references/account-configs.md`. This file is per-user and not committed to the repo.

---

## Step 5: Verify Your Setup

After onboarding, run a manual check to verify everything works:

```
/outbound-feed-monitor account:your_account
```

The skill will:
1. Search your Gmail for today's feed report emails
2. Parse and classify each feed
3. If failures found: create a Jira ticket on the DT board and post to Slack
4. If no failures: send you a DM confirming all clear

---

## What Happens on a Scheduled Run

Once scheduled, the skill runs automatically every Monday morning:

- **Failures detected** — creates a consolidated Jira ticket under the correct epic (PLD or Non-PLD Maintenance), posts a Slack message to #dataeng-support with a thread reply linking the ticket
- **No failures** — sends you a private Slack DM. No channel noise.

### Jira Ticket Details

Tickets are created with:
- **Project:** DT (Data Team board)
- **Issue type:** Data Issue
- **Epic:** Auto-matched based on your account + brand + PLD/Non-PLD
- **Labels:** client shortname, account shortname, `outbound-feed`
- **Start date:** Monday of detection
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

To monitor additional client accounts, run:

```
/outbound-feed-monitor
```

Choose "Add new account" during onboarding and provide the new account's details. Each account gets its own schedule and config.

---

## Python CLI

The `outbound-feed-monitor` CLI (installed in Step 2) is the primary execution engine for scheduled runs. It also supports manual use:

```bash
# Interactive terminal output (rich formatting)
outbound-feed-monitor --account myaccount

# Machine-readable JSON (used by the skill and scheduled tasks)
outbound-feed-monitor --account myaccount --json

# Dry run — parse and display only, no Slack/Jira actions
outbound-feed-monitor --account myaccount --dry-run

# Run for a specific past date
outbound-feed-monitor --account myaccount --date 2026-04-07
```

See [README.md](README.md) for full CLI reference.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Jira MCP connector disconnected | Re-authenticate in Claude Code settings. OAuth can expire after idle hours. |
| No emails found | Check that your Gmail has access to the feed report emails. Verify the sender email and subject line in your account config. |
| Wrong epic matched | Re-run onboarding and correct the brand or client name. The skill searches epics by `<Client> - <Brand> - [Non PLD/PLD] - Maintenance`. |
| Skill not found after install | Restart Claude Code. Check the skill directory is in the correct location. |

---

## Questions?

Open an issue on this repo or reach out to the Analytics & Strategy team.
