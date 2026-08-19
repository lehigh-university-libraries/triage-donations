# Book Donation Triage Scanner

ALPHA -- IN INITIAL DEVELOPMENT

A Flask app for a book-donation triage desk. A librarian scans a book's ISBN
with a USB barcode scanner; the app checks local holdings first via
SRU, falls back to a Library of Congress SRU lookup for title/author/Dewey
call number, maps the call number to a subject-selector librarian , and logs
every scan to a Google Sheet.

## Setup

### 1. Create a virtual environment and install dependencies

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure the app

Copy `config.yaml.example` to `config.yaml` and edit it.  Every option is
documented with comments in `config.yaml.example` — edit
`config.yaml` accordingly. 

### 3. Set up the Google Sheets service account

1. In Google Cloud Console, create (or reuse) a project and enable the
   **Google Sheets API**.
2. Create a service account and download its JSON key. Save it wherever
   `google_service_account_json_path` in `config.yaml` points (default:
   `service_account.json` in the project root). This file is gitignored —
   never commit it.
3. Open the target Google Sheet and share it with the service account's
   email address (found in the JSON key file), granting Editor access.
4. Set `google_sheet_id` in `config.yaml` to that Sheet's ID.

Each scan appends a row with: timestamp, ISBN, title, authors, disposition,
and call number.

### 4. Run the app

```powershell
venv\Scripts\Activate.ps1
flask run
```

Or: `python app.py` (runs Flask's dev server directly).

Open `http://127.0.0.1:5000/` in a browser on the kiosk machine, with a USB
barcode scanner attached — no keyboard/mouse interaction is needed once the
page is loaded; the scanner types the ISBN and sends Enter to trigger the
lookup automatically.

## Selector lookup

`selector.py`'s `get_selector(call_number)` looks up the subject-selector
librarian for a Dewey call number via the web service configured under
`selector` in `config.yaml` (see `config.yaml.example` for the API contract
and a link to a reference implementation). If that section is left
unconfigured, or the service returns anything other than exactly one
matching librarian, it falls back to a generic default selector.

## Docker deployment

Build and run with Docker:

```sh
docker build -t triage-donations .
docker run -v ./:/app -p 5000:5000 --rm --name triage-donations triage-donations
```

The container runs `gunicorn` (config in `gunicorn.conf.py`) against `app:app`
on port 5000. `config.yaml` and `service_account.json` aren't baked into the
image (see `.dockerignore`) — mount them in via the volume above, or bake
your own image on top with `COPY` if you'd rather not mount at runtime.
Set the `WORKERS` environment variable to change the gunicorn worker count
(default 4).
