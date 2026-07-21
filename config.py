from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"

DEFAULT_TIMEOUT_SECONDS = 8
DEFAULT_RECORD_SCHEMA = "marcxml"
DEFAULT_ISBN_INDEX = "isbn"


def _load_yaml():
    """Loads and parses config.yaml. Raises RuntimeError if the file is missing."""
    if not CONFIG_PATH.exists():
        raise RuntimeError(
            f"Missing {CONFIG_PATH}. Copy config.yaml.example to config.yaml "
            f"and fill in your environment's values."
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _require(section, key, section_name):
    """Returns section[key], raising RuntimeError if it's missing or blank."""
    value = (section or {}).get(key)
    if not value:
        raise RuntimeError(
            f"Missing required config value '{section_name}.{key}'. "
            f"Set it in config.yaml (see config.yaml.example)."
        )
    return value


def _build_endpoint_config(section, section_name):
    """Builds one SRU endpoint's config dict, applying defaults for anything
    section omits except sru_base_url, which is required."""
    return {
        "sru_base_url": _require(section, "sru_base_url", section_name),
        "timeout_seconds": float(
            (section or {}).get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
        ),
        "record_schema": (section or {}).get("record_schema", DEFAULT_RECORD_SCHEMA),
        "isbn_index": (section or {}).get("isbn_index", DEFAULT_ISBN_INDEX),
    }


def _build_remote_configs(remote_section):
    """Builds the {name: endpoint_config} dict for every entry under 'remote'."""
    remotes = {}
    for name, section in (remote_section or {}).items():
        remotes[name] = _build_endpoint_config(section, f"remote.{name}")
    return remotes


_data = _load_yaml()
_google_sheets = _data.get("google_sheets", {})
_selector = _data.get("selector", {})


class Config:
    LOCAL = _build_endpoint_config(_data.get("local"), "local")
    REMOTES = _build_remote_configs(_data.get("remote"))

    RECENT_SCANS_COUNT = int(_data.get("recent_scans_count", 3))

    GOOGLE_SERVICE_ACCOUNT_JSON_PATH = _google_sheets.get(
        "service_account_json_path", "service_account.json"
    )
    GOOGLE_SHEET_ID = _google_sheets.get("sheet_id") or None
    GOOGLE_SHEET_WORKSHEET_NAME = _google_sheets.get("worksheet_name", "Sheet1")

    SELECTOR_BASE_URL = _selector.get("base_url") or None
    SELECTOR_TIMEOUT_SECONDS = float(_selector.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
