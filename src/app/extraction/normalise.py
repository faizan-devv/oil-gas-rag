"""Turn the LLM's verbatim values into consistent, queryable ones."""

from datetime import date, datetime

from dateutil import parser as date_parser


def _text(value) -> str | None:
    """Trimmed string, or None for empty and placeholder values."""
    if value is None:
        return None
    value = str(value).strip()
    return None if value.lower() in {"", "null", "none", "n/a", "unknown"} else value


def parse_date(written: str) -> date | None:
    """Parse a date as an engineer writes it. Day-first, because the logs are
    British-style (17/03/2025). None when it is not a real calendar date."""
    try:
        # dateutil with dayfirst=True would read 2025-02-12 as 2 December.
        return date.fromisoformat(written)
    except ValueError:
        pass
    try:
        return date_parser.parse(written, dayfirst=True).date()
    except (ValueError, OverflowError):
        return None


def normalise(raw: dict, timestamp: str | None) -> dict:
    """Clean one extracted record. The date falls back to the entry timestamp
    when the text gives none; `date_source` records which was used, and
    `date_unparsed` carries a written date that could not be parsed so the
    consistency check can report it."""
    record = {
        "equipment_id": (_text(raw.get("equipment_id")) or "").upper() or None,
        "fault_code": (_text(raw.get("fault_code")) or "").upper() or None,
        "fault_description": _text(raw.get("fault_description")),
        "action_taken": _text(raw.get("action_taken")),
        "action_category": _text(raw.get("action_category")),
        "engineer_name": _text(raw.get("engineer_name")),
        "resolution_status": (_text(raw.get("resolution_status")) or "").lower() or None,
        "date": None,
        "date_source": None,
        "date_unparsed": None,
    }
    written = _text(raw.get("date"))
    if written:
        parsed = parse_date(written)
        if parsed:
            record["date"], record["date_source"] = parsed.isoformat(), "text"
        else:
            record["date_unparsed"] = written
    elif timestamp:
        try:
            record["date"] = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date().isoformat()
            record["date_source"] = "timestamp"
        except ValueError:
            pass
    return record
