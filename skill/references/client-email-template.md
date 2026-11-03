# Client Email Template — Failed Feed Delivery

Used by SKILL.md Step 4B. Reply-all on the report email that contains the failed rows, so the client
sees it in the same thread as the failure notice. Goal: tell them before they have to ask.

## Tone

Match how the team already writes to the client: warm, short, plain language. 3–5 lines.
No tables, no source table names, no internal detail. Name the files exactly as in the report
so the client can match them.

## Proactive (client has not replied yet)

```
Hi <client first names or "team">,

Heads up - <N> of today's files didn't go through:
<FILE_NAME_1>
<FILE_NAME_2>

Our team is already looking into it, and we'll resend them as soon as they're ready.

Thanks,
<signoff_name>
```

## Client already asked

```
Thanks for flagging, <client first name>!

We caught this too and our team is already looking into the <short description, e.g. "two DCM files">.
We'll resend them as soon as they're ready.

Thanks,
<signoff_name>
```

## Rules

- `<N>` and file names come only from parsed rows with `Status = Failed` (excluding known exceptions).
- One file → "one of today's files didn't go through". All files in the email → "today's <feed> files didn't go through".
- Greeting: use first names of the client contacts on the To line if there are 1–2 regular senders
  (e.g. "Hi Vishnu and team,"), otherwise "Hi team,".
- No Jira or Slack links, billing codes, root-cause guesses, or promised dates.
- Plain hyphens, no em dashes.
