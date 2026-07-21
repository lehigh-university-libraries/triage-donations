import logging

import gspread

logger = logging.getLogger(__name__)

HEADER_ROW = ["Timestamp", "ISBN", "Title", "Authors", "Disposition", "Call Number"]

_worksheet = None
_enabled = False


def init(config):
    """Connects to the configured Google Sheet at startup, adding a header row
    if it's currently blank. If Sheets isn't configured (google_sheets section
    commented out, or sheet_id left blank) or the connection fails, logs a
    warning once and leaves Sheets logging disabled for the rest of the
    process — append_scan_row then becomes a no-op instead of failing on
    every single scan.
    """
    global _worksheet, _enabled

    if not config.GOOGLE_SHEET_ID:
        logger.warning(
            "Google Sheets logging is disabled (no google_sheets.sheet_id "
            "configured) — scan results will not be appended to a Sheet."
        )
        return

    try:
        client = gspread.service_account(filename=config.GOOGLE_SERVICE_ACCOUNT_JSON_PATH)
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        worksheet = sheet.worksheet(config.GOOGLE_SHEET_WORKSHEET_NAME)

        if not worksheet.acell("A1").value:
            worksheet.append_row(HEADER_ROW, value_input_option="USER_ENTERED")

        _worksheet = worksheet
        _enabled = True
    except Exception:
        logger.exception("Failed to connect to Google Sheets at startup — Sheets logging is disabled")


def append_scan_row(result):
    """Appends a row to the configured Google Sheet. Returns an error string on
    failure; never raises, since a Sheets outage must not block the scan
    response. Returns None immediately if Sheets logging is disabled.
    """
    if not _enabled:
        return None

    try:
        _worksheet.append_row(
            [
                result["timestamp"],
                result["isbn"],
                result["title"] or "",
                "; ".join(result["authors"]) if result["authors"] else "",
                result["disposition"],
                result["call_number"] or "",
            ],
            value_input_option="USER_ENTERED",
        )
        return None
    except Exception as exc:
        logger.exception("Failed to append scan row to Google Sheet")
        return f"Sheets append failed: {exc}"
