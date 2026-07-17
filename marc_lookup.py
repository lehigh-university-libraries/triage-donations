import io
import logging
import re
from xml.etree import ElementTree as ET

import requests
from pymarc import marcxml as pymarc_marcxml

logger = logging.getLogger(__name__)

SRW_NS = {"zs": "http://www.loc.gov/zing/srw/"}
MARCXML_NS = {"marc": "http://www.loc.gov/MARC21/slim"}

ISBN10_RE = re.compile(r"^\d{9}[\dX]$")
ISBN13_RE = re.compile(r"^97[89]\d{10}$")


def normalize_and_validate_isbn(raw):
    """Returns (cleaned_isbn_or_None, is_structurally_valid)."""
    if not raw:
        return None, False
    cleaned = re.sub(r"[\s\-]", "", raw.strip())
    if not cleaned:
        return None, False

    if ISBN13_RE.match(cleaned):
        return cleaned, _isbn13_checksum_ok(cleaned)

    upper = cleaned.upper()
    if ISBN10_RE.match(upper):
        return upper, _isbn10_checksum_ok(upper)

    digits_only = re.sub(r"[^\dXx]", "", cleaned).upper()
    return (digits_only or None), False


def _isbn13_checksum_ok(isbn):
    """Returns True if isbn's ISBN-13 check digit is valid."""
    total = 0
    for i, ch in enumerate(isbn):
        digit = int(ch)
        total += digit if i % 2 == 0 else digit * 3
    return total % 10 == 0


def _isbn10_checksum_ok(isbn):
    """Returns True if isbn's ISBN-10 check digit is valid."""
    total = 0
    for i, ch in enumerate(isbn):
        value = 10 if ch == "X" else int(ch)
        total += value * (10 - i)
    return total % 11 == 0


def query_endpoint(isbn, endpoint_config, max_records):
    """Queries one SRU endpoint for isbn. Returns (records, error_message_or_None)."""
    params = {
        "version": "1.1",
        "operation": "searchRetrieve",
        "startRecord": "1",
        "maximumRecords": str(max_records),
        "recordSchema": endpoint_config["record_schema"],
        "query": f"{endpoint_config['isbn_index']}={isbn}",
    }
    base_url = endpoint_config["sru_base_url"]
    try:
        resp = requests.get(base_url, params=params, timeout=endpoint_config["timeout_seconds"])
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        return [], f"SRU request to {base_url} failed: {exc}"

    try:
        records = parse_sru_response(resp.content)
    except ET.ParseError as exc:
        return [], f"SRU response from {base_url} was not valid XML: {exc}"

    return records, None


def _parse_marcxml_record_data(record_data_el):
    """Parses one <recordData> element's embedded MARCXML into pymarc Records."""
    marc_el = record_data_el.find("marc:record", MARCXML_NS)
    if marc_el is None:
        # some gateways omit the namespace on the embedded <record>
        marc_el = record_data_el.find("record")
    if marc_el is None:
        return []
    xml_fragment = ET.tostring(marc_el)
    return pymarc_marcxml.parse_xml_to_array(io.BytesIO(xml_fragment))


def parse_sru_response(xml_bytes):
    """Given raw SRU searchRetrieveResponse XML bytes, return a list of pymarc
    Record objects. This app only supports SRU endpoints that return embedded
    MARCXML in <recordData> — every recordSchema value in use (including
    FOLIO's "usmarc", which is FOLIO's alias for the same MARCXML format
    LOC calls "marcxml") is parsed the same way.
    """
    root = ET.fromstring(xml_bytes)

    num_records_el = root.find(".//zs:numberOfRecords", SRW_NS)
    if num_records_el is None or int(num_records_el.text or "0") == 0:
        return []

    records = []
    for record_data_el in root.findall(".//zs:recordData", SRW_NS):
        parsed = _parse_marcxml_record_data(record_data_el)
        if not parsed:
            logger.warning("Unrecognized recordData shape: %s", ET.tostring(record_data_el)[:300])
            continue
        records.extend(parsed)

    return records


def extract_bib_info(record):
    """record: a pymarc.Record. Returns {'title': str|None, 'authors': [str], 'dewey': str|None}."""
    title = None
    f245 = record.get_fields("245")
    if f245:
        parts = f245[0].get_subfields("a", "b")
        joined = " ".join(p.strip().rstrip("/:,;") for p in parts).strip()
        title = joined or None

    authors = []
    for tag in ("100", "110", "111"):
        for field in record.get_fields(tag):
            subs = field.get_subfields("a", "b", "c", "d")
            name = " ".join(s.strip() for s in subs).strip().rstrip(",")
            if name:
                authors.append(name)

    for field in record.get_fields("700"):
        subs = field.get_subfields("a", "d")
        name = " ".join(s.strip() for s in subs).strip().rstrip(",")
        if name and name not in authors:
            authors.append(name)

    dewey = None
    f082 = record.get_fields("082")
    if f082:
        raw = f082[0].get_subfields("a")
        if raw:
            dewey = normalize_dewey(raw[0])

    return {"title": title, "authors": authors, "dewey": dewey}


def normalize_dewey(raw):
    """Cleans up a raw 082 $a subfield value into a plain Dewey call number string."""
    cleaned = raw.strip().rstrip(".")
    cleaned = cleaned.replace("/", "")
    return cleaned


def lookup_isbn(isbn, is_structurally_valid, config, selector_lookup):
    """Looks up isbn against the local catalog, then each configured remote in
    turn, and returns a single scan result dict (see _build_result)."""
    warnings = []

    if not isbn:
        return _build_result(isbn, is_structurally_valid, None, [], "not_found",
                              "Invalid ISBN", None, None, warnings)

    local_records, local_err = query_endpoint(isbn, config.LOCAL, 1)
    if local_err:
        warnings.append(local_err)

    if local_records:
        try:
            info = extract_bib_info(local_records[0])
        except Exception as exc:
            logger.exception("Failed to extract fields from local record")
            warnings.append(f"Failed to parse local MARC record: {exc}")
            info = None

        if info is not None:
            return _build_result(isbn, is_structurally_valid, info["title"], info["authors"],
                                  "local", "Already in collection", None, None, warnings)

    fallback_info = None
    fallback_source = None

    for name, remote_config in config.REMOTES.items():
        records, err = query_endpoint(isbn, remote_config, 1)
        if err:
            warnings.append(err)
            continue
        if not records:
            continue

        try:
            info = extract_bib_info(records[0])
        except Exception as exc:
            logger.exception("Failed to extract fields from %s record", name)
            warnings.append(f"Failed to parse record from {name}: {exc}")
            continue

        if info["dewey"]:
            selector_name = selector_lookup(info["dewey"])
            disposition = f"Dewey {info['dewey']} — see {selector_name}"
            return _build_result(isbn, is_structurally_valid, info["title"], info["authors"],
                                  name, disposition, info["dewey"], selector_name, warnings)

        if fallback_info is None:
            fallback_info = info
            fallback_source = name

    if fallback_info is not None:
        selector_name = selector_lookup("")
        disposition = f"Found at {fallback_source}, no Dewey number — see {selector_name}"
        return _build_result(isbn, is_structurally_valid, fallback_info["title"], fallback_info["authors"],
                              fallback_source, disposition, None, selector_name, warnings)

    return _build_result(isbn, is_structurally_valid, None, [], "not_found",
                          "Not found", None, None, warnings)


def _build_result(isbn, isbn_valid, title, authors, source, disposition, call_number, selector, warnings):
    """Assembles the scan result dict returned by lookup_isbn."""
    from datetime import datetime, timezone

    return {
        "isbn": isbn,
        "isbn_valid": isbn_valid,
        "title": title,
        "authors": authors,
        "source": source,
        "disposition": disposition,
        "call_number": call_number,
        "selector": selector,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "warnings": warnings,
    }
