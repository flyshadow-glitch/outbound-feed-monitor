# outbound-feed-monitor

Monitors client outbound feed pipeline emails and alerts the team on failures — automatically creating Jira tickets on the DT board and posting alerts to Slack.

**Two ways to use this tool:**

| Mode | What it does | Who it's for |
|---|---|---|
| **Claude Skill** (recommended) | Scheduled checks via Claude Code (day/time configurable). Auto-creates Jira tickets, posts Slack alerts, DMs you a summary. | Any analyst or DE team member with Claude Code |
| **Python CLI** (fallback) | Run feed checks from the terminal. Rich output, no Jira/Slack. | CI/CD, debugging, or when Claude Code is unavailable |

## Quick Start (Claude Skill)

See **[INSTALL.md](INSTALL.md)** for the full installation and onboarding guide.

```
/outbound-feed-monitor
```

The skill walks you through setup in ~5 minutes. Once configured, it runs automatically on your chosen schedule with zero manual intervention.

---

## Python CLI (Phase 1)

The CLI below is the original Phase 1 implementation. It handles email parsing and classification but does not create Jira tickets or Slack alerts. Use it for debugging or offline checks.

---

## Prerequisites

- Python 3.11+
- A Google account that receives the feed report emails
- A `credentials.json` file for Gmail OAuth (see below)

---

## 1. Google Cloud Setup (Gmail OAuth)

> **Most users skip this section.** If your team already has a `credentials.json` file, just place it in your working directory and run the CLI — a browser window will open for you to sign in. See [INSTALL.md](INSTALL.md) Path A.
>
> This section is for the **admin who creates the Google Cloud project the first time**. It only needs to happen once per team. Share the resulting `credentials.json` with your teammates.

You need a `credentials.json` file to authenticate with Gmail.

### Step 1: Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown (top left) → **New Project**
3. Name it `outbound-feed-monitor` → **Create**

### Step 2: Enable the Gmail API

1. In the left sidebar: **APIs & Services → Library**
2. Search for **Gmail API** → click it → **Enable**

### Step 3: Configure the OAuth consent screen

1. **APIs & Services → OAuth consent screen**
2. User Type: **Internal** (if your Google account is a Google Workspace account — this skips the verification requirement)
   - If you're using a personal Gmail account, choose **External** and add your email as a test user
3. Fill in: App name (`outbound-feed-monitor`), User support email, Developer contact email
4. Click **Save and Continue** through all screens (no scopes needed here)

### Step 4: Create OAuth credentials

1. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
2. Application type: **Desktop app**
3. Name: `outbound-feed-monitor`
4. Click **Create**
5. Click **Download JSON** — save the file as `credentials.json` in the project root

### Step 5: First run (browser auth)

On your first `python monitor.py` run, a browser window will open asking you to
authorize the app. Sign in with the Google account that receives the feed emails.
A `token.json` file is saved in the project root. Subsequent runs use this token
automatically (auto-refreshed — no browser prompt needed).

> **Security note:** `credentials.json` and `token.json` contain auth secrets.
> Do not commit them to version control. Both are in `.gitignore`.

---

## 2. Installation

```bash
# Clone or download the project
cd outbound-feed-monitor

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Copy env template (credentials are in files, not .env — for Phase 2 only)
cp .env.example .env
```

Place `credentials.json` in the project root (from Step 4 above).

---

## 3. Usage

```bash
python monitor.py --account <shortname> [--date YYYY-MM-DD] [--dry-run] [--test] [--no-jira]
```

| Flag | Description |
|---|---|
| `--account` | Required. Account shortname from `accounts.yaml` |
| `--date` | Optional. `YYYY-MM-DD`. Defaults to today. |
| `--dry-run` | Parse and display only. No Slack or Jira actions dispatched. |
| `--test` | *(Phase 2)* Route Slack to DM instead of production channel. |
| `--no-jira` | *(Phase 2)* Skip Jira ticket creation. |

---

## 4. Adding a New Account

Add a new block to `config/accounts.yaml`:

```yaml
accounts:
  myaccount:    # shortname used with --account flag
    account_name: "Client - Account Name"
    email_subject: "Client - Account: Outbound Feed Report"
    sender_email: "pipeline-sender@example.net"
    cadence_day: Monday
    expected_email_count: 2

    feed_types:
      - name: "Media"
        file_patterns: ["_GA_", "_BING_"]
        table_patterns: ["google_ads", "bing_ads"]
        notes: ""

    known_exceptions: []

    slack:
      production_channel_id: CXXXXXXXXXX
      production_channel: "#your-alert-channel"
      test_user_id: UXXXXXXXXXX

    jira:
      production_project_key: DT
      test_project_key: TEST
      cloud_id: "<your-cloud-id>"
      instance: "<your-instance>.atlassian.net"
      labels: ["client-shortname", "account-shortname", "outbound-feed"]
```

Then run: `python monitor.py --account myaccount --dry-run`

No code changes needed. The feed types, email patterns, and known exceptions
are all driven by config.

---

## 5. Classification Logic

Each row in the email body is classified in this order:

| Condition | Result |
|---|---|
| `source_table` matches a `known_exceptions` entry | ℹ️  INFO |
| `status == "Failed"` | 🔴 FAILURE |
| `status == "Exported"` and `row_count == 0` | 🟡 WARNING |
| `status == "Exported"` and null columns present | 🟡 WARNING |
| `status == "Exported"` and `row_count > 0` | ✅ ALL CLEAR |
| Expected email not received | 🔴 FAILURE (account level) |

The overall account status is the worst severity across all rows.

---

## 6. Demo Walkthrough (5 minutes)

### Step 1: Dry run — show parsing

```bash
python monitor.py --account myaccount --date 2026-03-30 --dry-run
```

Expected output:
```
────────── DRY RUN — no actions will be dispatched ──────────
Searching Gmail for <Account Name> emails on 2026-03-30...
Found 3 email(s) (expected 3).

<Account Name> — Outbound Feed Check — 2026-03-30
✅  Overall status: ALL CLEAR

 Feed Type         Files  Status       Problem Tables
 ──────────────── ─────── ──────────── ──────────────────────────────────────
 Media (Non-PLD)     11  ✅ ALL CLEAR  —
 PLD                  2  ✅ ALL CLEAR  —
 SEO                  2  ✅ ALL CLEAR  —

  Emails found:  3/3
  Slack alert:   skipped (--dry-run)
  Jira ticket:   skipped (--dry-run)
```

### Step 2: Off-cadence date check

```bash
python monitor.py --account myaccount --dry-run
```

If today is not the configured cadence day, you'll see a warning. The tool still
runs and reports what it finds.

### Step 3: Understanding known exceptions

Open `config/accounts.yaml` and look at `known_exceptions`:

```yaml
known_exceptions:
  - source_table: some_vendor_table
    condition: "Failed OR 0 rows"
    severity: INFO
    reason: >
      This table returns 0 rows when no active campaign is running.
      This is expected — not a pipeline failure.
```

Tables matching a known exception are classified as INFO (not FAILURE). No Slack
alert or Jira ticket is created for known exceptions alone.

### Step 4: Simulating a failure

Temporarily add a fake exception to `accounts.yaml` with a source table that
does NOT match a known exception, then run with `--dry-run` to see the FAILURE
classification and row detail output.

---

## 7. Project Structure

```
outbound-feed-monitor/
├── README.md
├── INSTALL.md                ← Skill installation + onboarding guide
├── requirements.txt
├── .env.example
├── credentials.json          ← download from Google Cloud (not committed)
├── token.json                ← auto-generated on first run (not committed)
├── config/
│   ├── accounts.example.yaml ← template — copy to accounts.yaml
│   └── accounts.yaml         ← your account config (gitignored)
├── monitor.py                ← CLI entrypoint
├── skill/                    ← Claude Code skill files
│   ├── SKILL.md              ← Main skill definition (8-step workflow)
│   └── references/
│       ├── account-configs.md    ← Account profile template + Jira field reference
│       ├── feed-types.md         ← Feed classification rules
│       ├── jira-template.md      ← Jira ticket description template
│       ├── slack-template.md     ← Slack message format spec
│       └── user-config.md        ← Per-user config (populated during onboarding)
├── core/
│   ├── gmail_reader.py       ← Gmail OAuth + search + HTML parse
│   ├── feed_classifier.py    ← FAILURE/WARNING/INFO/ALL CLEAR logic
│   ├── slack_alerter.py      ← Slack parent message + thread reply (Phase 2)
│   └── jira_manager.py       ← dedup check then create or comment (Phase 2)
└── scheduler/
    └── generate_apps_script.py  ← generates scheduler config (Phase 2)
```

---

## 8. Status

| Feature | Status |
|---|---|
| Gmail search + Chrome body reading + classification (Skill) | Done |
| Rich terminal output (CLI) | Done |
| Claude Skill — onboarding flow | Done |
| Claude Skill — Jira ticket creation (DT board, full field mapping) | Done |
| Claude Skill — Slack alerts (channel + thread reply) | Done |
| Claude Skill — scheduled runs (day/time configurable) | Done |
| Multi-account simultaneous monitoring | Planned |
| Billing code auto-sync with Genome | Planned |

---

## Troubleshooting

**`credentials.json not found`**
Download it from Google Cloud Console (APIs & Services → Credentials → your Desktop app → Download JSON) and place it in the project root.

**`Re-authentication required`**
Delete `token.json` and re-run. A browser window will open for you to sign in again.

**`Account 'xyz' not found in accounts.yaml`**
Check that your `--account` value matches a key in `config/accounts.yaml`.

**Found 0 emails on the expected cadence day**
Check that you're authenticated with the correct Google account (the one that receives the feed emails). Verify by searching Gmail for the expected subject line from your `accounts.yaml` config.
