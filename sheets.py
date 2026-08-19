import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import gspread

logger = logging.getLogger(__name__)

HEADER_ROW = [
    "Timestamp",
    "Input",
    "ISBN",
    "Title",
    "Authors",
    "Disposition",
    "Call Number",
    "Publication Date",
    "Imprint",
]

_worksheet = None
_enabled = False
_timezone = ZoneInfo("UTC")


def init(config):
    """Connects to the configured Google Sheet at startup, adding a header row
    if it's currently blank. If Sheets isn't configured (google_sheets section
    commented out, or sheet_id left blank) or the connection fails, logs a
    warning once and leaves Sheets logging disabled for the rest of the
    process — append_scan_row then becomes a no-op instead of failing on
    every single scan.
    """
    global _worksheet, _enabled, _timezone

    _timezone = ZoneInfo(config.GOOGLE_SHEET_TIMEZONE)

    if not config.GOOGLE_SHEET_ID:
        logger.warning(
            "Google Sheets logging is disabled (no google_sheets.sheet_id "
            "configured) — scan results will not be appended to a Sheet."
        )
        return

    try:
        client = gspread.service_account(
            filename=config.GOOGLE_SERVICE_ACCOUNT_JSON_PATH
        )
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        worksheet = sheet.worksheet(config.GOOGLE_SHEET_WORKSHEET_NAME)

        if not worksheet.acell("A1").value:
            worksheet.append_row(HEADER_ROW, value_input_option="USER_ENTERED")
            worksheet.freeze(rows=1)

        _worksheet = worksheet
        _enabled = True
    except Exception:
        logger.exception(
            "Failed to connect to Google Sheets at startup — Sheets logging is disabled"
        )


def _format_timestamp_for_sheets(iso_timestamp):
    """Converts an ISO-8601 UTC timestamp (e.g.
    '2026-08-17T14:32:01.123456+00:00') to the configured display timezone
    and reformats it as a plain 'YYYY-MM-DD HH:MM:SS' string, since Google
    Sheets doesn't recognize the 'T' separator or a timezone offset as a
    date/time value."""
    local_dt = datetime.fromisoformat(iso_timestamp).astimezone(_timezone)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")


def append_scan_row(input, result):
    """Appends a row to the configured Google Sheet. Returns an error string on
    failure; never raises, since a Sheets outage must not block the scan
    response. Returns None immediately if Sheets logging is disabled.
    """
    if not _enabled:
        return None

    try:
        _worksheet.append_row(
            [
                _format_timestamp_for_sheets(result["timestamp"]),
                input,
                result["isbn"],
                result["title"] or "",
                "; ".join(result["authors"]) if result["authors"] else "",
                result["disposition"],
                result["call_number"] or "",
                result["publication_date"] or "",
                result["imprint"] or "",
            ],
            value_input_option="USER_ENTERED",
        )
        return None
    except Exception as exc:
        logger.exception("Failed to append scan row to Google Sheet")
        return f"Sheets append failed: {exc}"
