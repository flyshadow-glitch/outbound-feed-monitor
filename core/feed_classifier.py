"""Feed export result classifier.

Implements the classification decision table from the design doc:

  1. Check known_exceptions first — if row matches, return INFO
  2. status == "Failed"                              → FAILURE
  3. status == "Exported" AND row_count == 0         → WARNING
  4. status == "Exported" AND null_columns non-empty → WARNING
  5. status == "Exported" AND row_count > 0          → ALL CLEAR

Account-level severity is the worst severity across all rows.
A missing email (fewer than expected_email_count received) is also FAILURE.
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Severity constants
# ---------------------------------------------------------------------------

ALL_CLEAR = "ALL_CLEAR"
INFO = "INFO"
WARNING = "WARNING"
FAILURE = "FAILURE"

# Used for max() comparisons
SEVERITY_RANK: dict[str, int] = {
    ALL_CLEAR: 0,
    INFO: 1,
    WARNING: 2,
    FAILURE: 3,
}

SEVERITY_EMOJI: dict[str, str] = {
    ALL_CLEAR: "✅",
    INFO: "ℹ️ ",
    WARNING: "🟡",
    FAILURE: "🔴",
}

SEVERITY_LABEL: dict[str, str] = {
    ALL_CLEAR: "ALL CLEAR",
    INFO: "INFO",
    WARNING: "WARNING",
    FAILURE: "FAILURE",
}

# Null Columns values that mean "no nulls" — do not trigger WARNING
_NULL_CLEAR_VALUES = {"N/A", "", "[]", "[ ]"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ClassifiedRow:
    file_name: str
    status: str
    source_table: str
    report_from: str
    report_to: str
    row_count: int
    null_columns: str
    feed_type: str
    severity: str
    exception_reason: Optional[str] = None


@dataclass
class FeedTypeSummary:
    name: str
    rows: list[ClassifiedRow] = field(default_factory=list)

    @property
    def severity(self) -> str:
        if not self.rows:
            return ALL_CLEAR
        return max(self.rows, key=lambda r: SEVERITY_RANK[r.severity]).severity

    @property
    def file_count(self) -> int:
        return len(self.rows)

    @property
    def problem_tables(self) -> list[str]:
        """Source tables with FAILURE or WARNING (for terminal display)."""
        return [
            r.source_table
            for r in self.rows
            if r.severity in (FAILURE, WARNING)
        ]

    @property
    def info_tables(self) -> list[str]:
        """Source tables that are known exceptions (INFO)."""
        return [r.source_table for r in self.rows if r.severity == INFO]


@dataclass
class AccountResult:
    account_shortname: str
    account_name: str
    target_date: str
    emails_found: int
    emails_expected: int
    feed_summaries: list[FeedTypeSummary] = field(default_factory=list)

    @property
    def overall_severity(self) -> str:
        ranks = [SEVERITY_RANK[s.severity] for s in self.feed_summaries]
        if self.emails_found < self.emails_expected:
            ranks.append(SEVERITY_RANK[FAILURE])
        if not ranks:
            return FAILURE if self.emails_found == 0 else ALL_CLEAR
        worst = max(ranks)
        # Reverse lookup
        return next(k for k, v in SEVERITY_RANK.items() if v == worst)


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def _match_exception(row: dict, known_exceptions: list[dict]) -> Optional[dict]:
    """Return the first matching known_exception config, or None.

    Condition enum values:
      "Failed"          — matches when status == "Failed"
      "0 rows"          — matches when row_count == 0
      "Failed OR 0 rows" — matches either condition
    """
    for exc in known_exceptions:
        if row["source_table"] != exc.get("source_table", ""):
            continue

        condition = exc.get("condition", "")
        status = row["status"]
        row_count = row["row_count"]

        if condition == "Failed" and status == "Failed":
            return exc
        if condition == "0 rows" and row_count == 0:
            return exc
        if condition == "Failed OR 0 rows" and (status == "Failed" or row_count == 0):
            return exc

    return None


def _detect_feed_type(row: dict, feed_types: list[dict]) -> str:
    """Assign a feed type by matching file_name or source_table patterns.

    Evaluates feed_types in config order. For each feed type, tries
    file_patterns first (substring match on file_name), then table_patterns
    (substring match on source_table). First match wins.

    Returns "Unknown" if no pattern matches.
    """
    for ft in feed_types:
        for pattern in ft.get("file_patterns", []):
            if pattern in row["file_name"]:
                return ft["name"]
        for pattern in ft.get("table_patterns", []):
            if pattern in row["source_table"]:
                return ft["name"]
    return "Unknown"


def _classify_row(row: dict, account_config: dict) -> ClassifiedRow:
    """Classify a single parsed row using the decision table."""
    known_exceptions = account_config.get("known_exceptions", [])
    feed_types = account_config.get("feed_types", [])

    feed_type = _detect_feed_type(row, feed_types)

    # Step 1: known exception check (highest priority)
    exc = _match_exception(row, known_exceptions)
    if exc:
        return ClassifiedRow(
            file_name=row["file_name"],
            status=row["status"],
            source_table=row["source_table"],
            report_from=row["report_from"],
            report_to=row["report_to"],
            row_count=row["row_count"],
            null_columns=row["null_columns"],
            feed_type=feed_type,
            severity=exc.get("severity", INFO),
            exception_reason=exc.get("reason", "Known exception"),
        )

    # Step 2–5: standard classification
    if row["status"] == "Failed":
        severity = FAILURE
    elif row["row_count"] == 0:
        severity = WARNING
    elif row["null_columns"].strip() not in _NULL_CLEAR_VALUES:
        severity = WARNING
    else:
        severity = ALL_CLEAR

    return ClassifiedRow(
        file_name=row["file_name"],
        status=row["status"],
        source_table=row["source_table"],
        report_from=row["report_from"],
        report_to=row["report_to"],
        row_count=row["row_count"],
        null_columns=row["null_columns"],
        feed_type=feed_type,
        severity=severity,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def classify_account(
    emails_data: list[list[dict]],
    account_config: dict,
    target_date: str,
) -> AccountResult:
    """Classify all rows from all emails for an account.

    Args:
        emails_data:    List of parsed row lists (one list per email).
        account_config: Account config dict from accounts.yaml (with account_shortname injected).
        target_date:    Date string for display (YYYY-MM-DD).

    Returns:
        AccountResult with per-feed-type summaries and overall severity.
    """
    account_shortname = account_config.get("account_shortname", "unknown")
    account_name = account_config.get("account_name", "Unknown Account")
    expected_count = account_config.get("expected_email_count", 1)
    feed_types = account_config.get("feed_types", [])

    # Build feed type buckets in config order, plus Unknown
    ordered_names = [ft["name"] for ft in feed_types]
    feed_type_map: dict[str, FeedTypeSummary] = {
        name: FeedTypeSummary(name=name) for name in ordered_names
    }
    unknown_bucket = FeedTypeSummary(name="Unknown")

    # Classify every row from every email
    for email_rows in emails_data:
        for row in email_rows:
            classified = _classify_row(row, account_config)
            ft = classified.feed_type
            if ft in feed_type_map:
                feed_type_map[ft].rows.append(classified)
            else:
                unknown_bucket.rows.append(classified)

    # Build ordered summaries, only including feed types with rows
    summaries: list[FeedTypeSummary] = [
        feed_type_map[name] for name in ordered_names if feed_type_map[name].rows
    ]
    if unknown_bucket.rows:
        summaries.append(unknown_bucket)

    return AccountResult(
        account_shortname=account_shortname,
        account_name=account_name,
        target_date=target_date,
        emails_found=len(emails_data),
        emails_expected=expected_count,
        feed_summaries=summaries,
    )
