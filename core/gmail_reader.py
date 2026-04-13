"""Gmail OAuth + search + HTML email parser for outbound feed report emails.

Email format:
- MIME type: multipart/mixed with text/html body
- Body: HTML table with 7 columns per data row
- PLD emails include publisher breakdown sub-rows (skipped during parsing)
- Row counts are comma-formatted integers (e.g. "3,768", "3,124,032")
- Null Columns field is either "N/A" or "[]" (empty list)
"""

import base64
import re
import sys
from datetime import date, timedelta
from email import message_from_bytes
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_FILE = Path("token.json")
CREDENTIALS_FILE = Path("credentials.json")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_credentials() -> Credentials:
    """Load credentials from token.json, refreshing if needed.

    On first run, opens a browser for Google OAuth consent and saves token.json.
    On subsequent runs, loads and auto-refreshes the saved token.

    Raises:
        FileNotFoundError: If credentials.json is missing and no saved token exists.
        SystemExit: If re-authentication is required but cannot complete.
    """
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                # Refresh failed — need full re-auth
                creds = None

        if not creds:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    "credentials.json not found in the project root.\n"
                    "Download it from Google Cloud Console (APIs & Services → Credentials)\n"
                    "and place it here. See README for step-by-step instructions."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


def build_gmail_service():
    """Return an authenticated Gmail API service instance."""
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# ---------------------------------------------------------------------------
# Gmail search
# ---------------------------------------------------------------------------

def search_messages(service, query: str, max_results: int = 20) -> list[str]:
    """Search Gmail and return a list of message IDs matching the query."""
    result = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    messages = result.get("messages", [])
    return [m["id"] for m in messages]


def fetch_raw_message(service, msg_id: str) -> bytes:
    """Fetch a message as raw RFC 2822 bytes."""
    result = (
        service.users()
        .messages()
        .get(userId="me", id=msg_id, format="raw")
        .execute()
    )
    # Gmail returns base64url without padding — add == to be safe
    return base64.urlsafe_b64decode(result["raw"] + "==")


# ---------------------------------------------------------------------------
# MIME parsing
# ---------------------------------------------------------------------------

def extract_html_body(raw_bytes: bytes) -> Optional[str]:
    """Walk the MIME tree and return the text/html part as a string."""
    msg = message_from_bytes(raw_bytes)
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return None


# ---------------------------------------------------------------------------
# HTML table parser
# ---------------------------------------------------------------------------

class _FeedTableParser(HTMLParser):
    """Parse the feed report HTML table into a list of row dicts.

    Handles two row types present in PLD emails:
      - Publisher Counts header: <td colspan="7"> — skipped
      - Publisher breakdown:     first <td> has style="padding-left:40px" — skipped

    Only standard 7-cell data rows are returned.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._in_tbody = False
        self._in_tr = False
        self._in_td = False
        self._all_rows: list[list[tuple[dict, str]]] = []  # [(attrs, text), ...]
        self._current_cells: list[tuple[dict, str]] = []
        self._current_td_attrs: dict = {}
        self._current_td_text: str = ""

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attrs_dict = dict(attrs)
        if tag == "tbody":
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self._in_tr = True
            self._current_cells = []
        elif tag == "td" and self._in_tr:
            self._in_td = True
            self._current_td_attrs = attrs_dict
            self._current_td_text = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "tbody":
            self._in_tbody = False
        elif tag == "tr" and self._in_tbody:
            self._in_tr = False
            if self._current_cells:
                self._all_rows.append(self._current_cells)
        elif tag == "td" and self._in_td:
            self._in_td = False
            text = re.sub(r"\s+", " ", self._current_td_text).strip()
            self._current_cells.append((self._current_td_attrs, text))

    def handle_data(self, data: str) -> None:
        if self._in_td:
            self._current_td_text += data

    def get_data_rows(self) -> list[dict]:
        """Return only standard 7-cell data rows as dicts."""
        data_rows = []
        for cells in self._all_rows:
            if not cells:
                continue
            first_attrs, _ = cells[0]

            # Skip "Publisher Counts:" header (single cell spanning all columns)
            if first_attrs.get("colspan") == "7":
                continue

            # Skip publisher breakdown rows (indented with padding-left:40px)
            if "padding-left:40px" in first_attrs.get("style", ""):
                continue

            # Must be a standard 7-cell row
            if len(cells) != 7:
                continue

            data_rows.append({
                "file_name": cells[0][1],
                "status": cells[1][1],
                "source_table": cells[2][1],
                "report_from": cells[3][1],
                "report_to": cells[4][1],
                "row_count": _parse_row_count(cells[5][1]),
                "null_columns": cells[6][1],
            })

        return data_rows


def _parse_row_count(value: str) -> int:
    """Parse a comma-formatted integer string. Returns 0 on failure.

    Examples:
        "3,768"       → 3768
        "3,124,032"   → 3124032
        "0"           → 0
    """
    try:
        return int(value.replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0


def parse_html_body(html: str) -> list[dict]:
    """Parse a feed report HTML body into a list of row dicts."""
    parser = _FeedTableParser()
    parser.feed(html)
    return parser.get_data_rows()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def get_feed_emails(account_config: dict, target_date: date) -> tuple[list[list[dict]], int]:
    """Search Gmail for feed emails on target_date and parse each one.

    Searches for emails matching the account's subject + sender within a
    single-day window. Each found email is parsed into a list of row dicts.

    Args:
        account_config: Account config dict from accounts.yaml.
        target_date:    Date to search for emails.

    Returns:
        (emails_data, found_count) where:
          - emails_data is a list of parsed row lists, one per email found
          - found_count is the raw Gmail search result count (before parsing)
    """
    service = build_gmail_service()

    after = target_date.strftime("%Y/%m/%d")
    before = (target_date + timedelta(days=1)).strftime("%Y/%m/%d")

    query = (
        f'subject:"{account_config["email_subject"]}" '
        f'from:{account_config["sender_email"]} '
        f'after:{after} before:{before}'
    )

    msg_ids = search_messages(service, query)

    emails_data: list[list[dict]] = []
    for msg_id in msg_ids:
        raw = fetch_raw_message(service, msg_id)
        html = extract_html_body(raw)
        if html:
            rows = parse_html_body(html)
            if rows:
                emails_data.append(rows)

    return emails_data, len(msg_ids)
