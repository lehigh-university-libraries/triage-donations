import os

bind = "0.0.0.0:5000"
workers = int(os.environ.get("WORKERS", 4))


def on_starting(server):
    """Connects to the Google Sheet once in the master process before any
    workers are forked, so the worker-local sheets.init() calls in app.py
    don't race each other to write the header row on a blank sheet."""
    import sheets
    from config import Config

    sheets.init(Config)
