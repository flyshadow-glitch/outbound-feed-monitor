#!/usr/bin/env python3
"""outbound-feed-monitor — Monitor client outbound feed pipeline emails.

Phase 1: Gmail OAuth + email parsing + classification + rich terminal output.
Phase 2 (planned): Slack alerts, Jira ticket creation/deduplication, setup.py onboarding.

Usage:
    python monitor.py --account myaccount [--date YYYY-MM-DD] [--dry-run] [--json] [--test] [--no-jira]

Flags:
    --account   Required. Account shortname from accounts.yaml
    --date      Optional. YYYY-MM-DD. Defaults to today.
    --dry-run   Parse and display only. No Slack or Jira actions dispatched.
    --json      Output result as JSON to stdout instead of rich terminal display.
                Used by the Claude Code skill for headless/scheduled runs.
    --test      (Phase 2) Route Slack to DM instead of production channel.
    --no-jira   (Phase 2) Skip Jira ticket creation.
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from core.feed_classifier import (
    ALL_CLEAR,
    FAILURE,
    INFO,
    SEVERITY_EMOJI,
    SEVERITY_LABEL,
    SEVERITY_RANK,
    WARNING,
    AccountResult,
    classify_account,
)
from core.gmail_reader import get_feed_emails

console = Console()

ACCOUNTS_FILE = Path("config/accounts.yaml")
ENV_FILE = Path(".env")

# Severity → Rich colour
_SEVERITY_STYLE: dict[str, str] = {
    ALL_CLEAR: "bold green",
    INFO: "bold blue",
    WARNING: "bold yellow",
    FAILURE: "bold red",
}


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_accounts() -> dict:
    if not ACCOUNTS_FILE.exists():
        console.print("[red]config/accounts.yaml not found.[/red]")
        console.print("Run [bold]python setup.py[/bold] to configure your first account.")
        sys.exit(1)
    with open(ACCOUNTS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_account_config(accounts: dict, shortname: str) -> dict:
    accounts_map = accounts.get("accounts", {})
    if shortname not in accounts_map:
        available = ", ".join(accounts_map.keys())
        console.print(f"[red]Account '{shortname}' not found in accounts.yaml.[/red]")
        console.print(f"Available accounts: {available}")
        sys.exit(1)
    config = dict(accounts_map[shortname])
    config["account_shortname"] = shortname  # inject key as field
    return config


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor client outbound feed pipeline emails.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--account", required=True,
        help="Account shortname matching accounts.yaml",
    )
    parser.add_argument(
        "--date",
        help="Target date YYYY-MM-DD. Defaults to today.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and display only — no Slack or Jira actions.",
    )
    parser.add_argument(
        "--json", action="store_true", dest="output_json",
        help="Output result as JSON to stdout. Used by Claude Code skill for headless runs.",
    )
    parser.add_argument(
        "--test", action="store_true",
        help="(Phase 2) Route Slack alert to DM instead of production channel.",
    )
    parser.add_argument(
        "--no-jira", action="store_true",
        help="(Phase 2) Skip Jira ticket creation.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Terminal rendering
# ---------------------------------------------------------------------------

def render_header(result: AccountResult) -> None:
    overall = result.overall_severity
    emoji = SEVERITY_EMOJI[overall]
    label = SEVERITY_LABEL[overall]
    style = _SEVERITY_STYLE[overall]

    console.print(
        f"\n[bold]{result.account_name}[/bold] — "
        f"Outbound Feed Check — {result.target_date}"
    )
    console.print(
        f"{emoji}  Overall status: [{style}]{label}[/{style}]\n"
    )


def render_summary_table(result: AccountResult) -> None:
    """Render the per-feed-type summary table."""
    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold",
        expand=False,
        padding=(0, 1),
    )
    table.add_column("Feed Type", style="bold", min_width=18)
    table.add_column("Files", justify="right", min_width=5)
    table.add_column("Status", min_width=16)
    table.add_column("Problem Tables", min_width=35)

    for summary in result.feed_summaries:
        sev = summary.severity
        emoji = SEVERITY_EMOJI[sev]
        label = SEVERITY_LABEL[sev]
        style = _SEVERITY_STYLE[sev]

        # Problem tables: failures/warnings shown in red/yellow; info tables noted separately
        problem = summary.problem_tables
        info = summary.info_tables

        if problem:
            problem_str = ", ".join(problem)
        elif info:
            problem_str = f"{', '.join(info)} (known exception)"
        else:
            problem_str = "—"

        table.add_row(
            summary.name,
            str(summary.file_count),
            Text(f"{emoji} {label}", style=style),
            problem_str,
        )

    console.print(table)


def render_footer(
    result: AccountResult,
    dry_run: bool,
    test_mode: bool,
    no_jira: bool,
) -> None:
    """Render the action status footer lines."""
    found = result.emails_found
    expected = result.emails_expected
    emails_str = f"{found}/{expected}"

    if found < expected:
        missing = expected - found
        console.print(
            f"  Emails found:  [red]{emails_str}[/red] "
            f"({missing} email(s) missing — check Gmail)"
        )
    else:
        console.print(f"  Emails found:  [green]{emails_str}[/green]")

    if dry_run:
        console.print("  Slack alert:   [dim]skipped (--dry-run)[/dim]")
        console.print("  Jira ticket:   [dim]skipped (--dry-run)[/dim]")
    else:
        # Phase 2 will replace these lines with real action results
        console.print("  Slack alert:   [dim]not yet configured (Phase 2)[/dim]")
        if no_jira:
            console.print("  Jira ticket:   [dim]skipped (--no-jira)[/dim]")
        else:
            console.print("  Jira ticket:   [dim]not yet configured (Phase 2)[/dim]")


def render_row_detail(result: AccountResult) -> None:
    """Print per-row detail for failures/warnings (shown in dry-run or on FAILURE)."""
    problem_rows = [
        row
        for summary in result.feed_summaries
        for row in summary.rows
        if row.severity in (FAILURE, WARNING)
    ]
    if not problem_rows:
        return

    console.print("\n[bold]Row detail:[/bold]")
    detail = Table(box=box.MINIMAL, show_header=True, header_style="dim", expand=False)
    detail.add_column("Source Table", min_width=35)
    detail.add_column("Status", min_width=9)
    detail.add_column("Rows", justify="right", min_width=10)
    detail.add_column("Null Cols", min_width=8)
    detail.add_column("Date Range", min_width=24)

    for row in problem_rows:
        sev_style = _SEVERITY_STYLE[row.severity]
        detail.add_row(
            row.source_table,
            Text(row.status, style=sev_style),
            f"{row.row_count:,}",
            row.null_columns,
            f"{row.report_from} → {row.report_to}",
        )

    console.print(detail)


# ---------------------------------------------------------------------------
# JSON output (for Claude Code skill / headless scheduled runs)
# ---------------------------------------------------------------------------

def build_json_output(result: AccountResult) -> dict:
    """Serialize AccountResult to a dict suitable for json.dumps().

    The Claude Code skill parses this output to determine what to alert on.
    Schema is intentionally flat and stable — do not rename keys without
    updating the skill's SKILL.md Step 3 parsing instructions.
    """
    problem_rows = [
        {
            "file_name": row.file_name,
            "status": row.status,
            "source_table": row.source_table,
            "report_from": row.report_from,
            "report_to": row.report_to,
            "row_count": row.row_count,
            "null_columns": row.null_columns,
            "feed_type": row.feed_type,
            "severity": row.severity,
            "exception_reason": row.exception_reason,
        }
        for summary in result.feed_summaries
        for row in summary.rows
        if row.severity in (FAILURE, WARNING, INFO)
    ]

    return {
        "account": result.account_name,
        "account_shortname": result.account_shortname,
        "date": result.target_date,
        "overall_severity": result.overall_severity,
        "emails_found": result.emails_found,
        "emails_expected": result.emails_expected,
        "feed_summaries": [
            {
                "name": s.name,
                "severity": s.severity,
                "file_count": s.file_count,
                "problem_tables": s.problem_tables,
                "info_tables": s.info_tables,
            }
            for s in result.feed_summaries
        ],
        "problem_rows": problem_rows,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    load_dotenv(ENV_FILE)
    args = parse_args()

    # -- Dry-run banner
    if args.dry_run:
        console.rule("[yellow]DRY RUN — no actions will be dispatched[/yellow]")

    # -- Target date
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            console.print("[red]Invalid --date format. Expected YYYY-MM-DD.[/red]")
            sys.exit(1)
    else:
        target_date = date.today()

    # -- Load config
    accounts = load_accounts()
    account_config = get_account_config(accounts, args.account)

    # -- Cadence day warning
    cadence_day = account_config.get("cadence_day", "Monday")
    actual_day = target_date.strftime("%A")
    if actual_day != cadence_day:
        console.print(
            f"[yellow]⚠[/yellow]  {target_date} is a {actual_day}. "
            f"{account_config['account_name']} cadence is {cadence_day}. "
            f"Emails found may be 0.\n"
        )

    # -- Gmail search
    console.print(f"Searching Gmail for {account_config['account_name']} emails on {target_date}...")
    try:
        emails_data, found_count = get_feed_emails(account_config, target_date)
    except FileNotFoundError as exc:
        console.print(f"\n[red]Setup required:[/red] {exc}")
        sys.exit(1)
    except Exception as exc:
        console.print(f"\n[red]Gmail error:[/red] {exc}")
        raise

    console.print(
        f"Found [bold]{found_count}[/bold] email(s) "
        f"(expected {account_config['expected_email_count']})."
    )

    if found_count == 0:
        console.print(
            f"\n[red]🔴 FAILURE[/red] — No emails found for {target_date}.\n"
        )
        return

    # -- Classify
    result = classify_account(emails_data, account_config, str(target_date))

    # -- JSON mode (used by Claude Code skill for headless/scheduled runs)
    if args.output_json:
        print(json.dumps(build_json_output(result), indent=2))
        return

    # -- Render (interactive terminal)
    render_header(result)
    render_summary_table(result)

    # Show row detail on failures, warnings, or dry-run
    overall = result.overall_severity
    if args.dry_run or overall in (FAILURE, WARNING):
        render_row_detail(result)

    console.print()
    render_footer(result, args.dry_run, args.test, args.no_jira)
    console.print()


if __name__ == "__main__":
    main()
