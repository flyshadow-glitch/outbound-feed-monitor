# Slack Alert Template — Outbound Feed Issues

This template is account-generic. Replace `<ACCOUNT>` placeholders with values from the resolved config.

## When to use this template
Load this file in Step 5 of the skill workflow when composing the Slack alert.

---

## Message Format — Failure or Warning

**Two messages total. Nothing else.**

**Message 1 — Parent (thread header):**
```
:thread1: <stream> | <client> | <brand> | <affected feed types>
```
Example: `:thread1: Non-PLD | <client> | <brand> | DCM, SEO`

**Message 2 — Thread reply (ticket link only):**
```
Ticket: <JIRA_LINK>
```
Example: `Ticket: https://<instance>.atlassian.net/browse/DT-XXXX`

All failure detail goes into the Jira ticket description, not the Slack thread.
If Jira creation fails, omit Message 2 and note the error in chat only.

---

## Message Format — All Clear (DM only)

If ALL CLEAR and user has configured all-clear confirmations:
```
:white_check_mark: <ACCOUNT> Outbound — All feeds exported successfully for [DATE RANGE].
```

Send as a DM to the user, never to the production channel.

---

## Emoji Reference

| Emoji | Use |
|---|---|
| `:thread1:` | Thread header opener |
| `:white_check_mark:` | All clear |

---

## DM vs Channel Mode

- **Testing (DM):** Single message only: `:thread1: ...` header with ticket link inline.
- **Production channel:** Post parent first, capture `ts`, post ticket link as thread reply with `thread_ts`.
