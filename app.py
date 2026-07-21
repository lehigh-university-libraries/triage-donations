import logging

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

import marc_lookup
import selector
import sheets
from config import Config
from selector import get_selector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

sheets.init(Config)
selector.init(Config)


@app.route("/")
def index():
    """Renders the kiosk page, passing along the browser-side recent-scans row cap."""
    return render_template("index.html", recent_count=Config.RECENT_SCANS_COUNT)


@app.route("/api/scan", methods=["POST"])
def scan():
    """Looks up the scanned ISBN, logs it to Sheets, and returns the result as
    JSON. Returns a (JSON body, status code) tuple on invalid input (400);
    otherwise just the JSON body (Flask defaults to 200)."""
    payload = request.get_json(silent=True) or {}
    raw_isbn = payload.get("isbn", "")

    isbn, is_valid = marc_lookup.normalize_and_validate_isbn(raw_isbn)
    if not isbn:
        return jsonify(ok=False, error="invalid_isbn", message="No ISBN digits found in input"), 400

    result = marc_lookup.lookup_isbn(isbn, is_valid, Config, get_selector)

    sheets_error = sheets.append_scan_row(result)
    if sheets_error:
        result["warnings"].append(sheets_error)

    return jsonify(ok=True, result=result)


@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    """Converts any uncaught exception into a JSON error response instead of
    Flask's default HTML page. Returns a (JSON body, status code) tuple."""
    if isinstance(exc, HTTPException):
        return jsonify(ok=False, error="http_error", message=exc.description), exc.code

    logger.exception("Unhandled exception in request")
    return jsonify(ok=False, error="server_error", message=str(exc)), 500


if __name__ == "__main__":
    app.run(debug=True)
