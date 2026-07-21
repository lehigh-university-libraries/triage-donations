import logging

import requests

logger = logging.getLogger(__name__)

DEFAULT_SELECTOR = "General Collections Selector"

_base_url = None
_timeout_seconds = None


def init(config):
    """Configures the selector web service connection at startup. If it's not
    configured (selector section commented out, or base_url left blank), logs
    a warning once and get_selector() always falls back to the default
    selector without making any network call.
    """
    global _base_url, _timeout_seconds

    if not config.SELECTOR_BASE_URL:
        logger.warning(
            "Selector web service is not configured (no selector.base_url "
            "configured) — every call number will use the default selector."
        )
        return

    _base_url = config.SELECTOR_BASE_URL
    _timeout_seconds = config.SELECTOR_TIMEOUT_SECONDS


def get_selector(call_number):
    """Looks up the subject-selector librarian for call_number via the
    configured web service (a reference implementation is available at
    https://github.com/lehigh-university-libraries/librarian-call-numbers).
    Falls back to a generic default if the service isn't configured, the
    request fails, or anything other than exactly one librarian is returned.
    """
    if not call_number or not _base_url:
        return DEFAULT_SELECTOR

    try:
        resp = requests.get(
            _base_url, params={"callNumber": call_number}, timeout=_timeout_seconds
        )
        resp.raise_for_status()
        librarians = resp.json()
    except (requests.exceptions.RequestException, ValueError) as exc:
        logger.warning("Selector lookup failed for call number %r: %s", call_number, exc)
        return DEFAULT_SELECTOR

    if not isinstance(librarians, list) or len(librarians) != 1:
        return DEFAULT_SELECTOR

    librarian = librarians[0]
    name = f"{librarian.get('firstName', '').strip()} {librarian.get('lastName', '').strip()}".strip()
    return name or DEFAULT_SELECTOR
