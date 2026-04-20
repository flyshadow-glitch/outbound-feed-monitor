# User Configs — Outbound Feed Monitor

Each user who has completed onboarding has a config block below.
The skill reads this file on invocation to load the user's preferences
without re-asking setup questions.

To reconfigure: say "reconfigure feed monitor" or "change feed monitor settings".

---

<!-- Configs are added automatically during the onboarding flow (SKILL.md Step 0B). -->
<!-- Do not edit manually unless you know what you're doing. -->

## User: elin@klick.com

gmail: elin@klick.com
accounts: [adc]
slack_target: U059RTH6ZFC
slack_mode: dm
jira_enabled: true
jira_project_key: DT
jira_token_created: unknown
billing_code_nonpld: "71271"
billing_code_pld: "71271"
cst: Apex
client: Abbott
schedules:
  adc:
    enabled: true
    cron: "45 10 * * 1"
    task_id: feed-check-adc
