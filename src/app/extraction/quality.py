"""Completeness and consistency checks. A record that fails any check is quarantined."""

from app.catalog import ACTION_CATEGORIES, EQUIPMENT_ID_RE, FAULT_CODE_RE, RESOLUTION_STATUSES
from app.extraction.schema import REQUIRED_FIELDS

# Reason codes written to the quarantine file.
MISSING_FIELD = "MISSING_FIELD"
BAD_DATE = "BAD_DATE"
BAD_EQUIPMENT_ID = "BAD_EQUIPMENT_ID"
BAD_FAULT_CODE = "BAD_FAULT_CODE"
BAD_ENUM = "BAD_ENUM"
LLM_PARSE_ERROR = "LLM_PARSE_ERROR"


def completeness(record: dict) -> list[dict]:
    """Every required field is present. A date that was written but could not
    be parsed is a consistency failure, not a missing field."""
    return [
        {"code": MISSING_FIELD, "field": field, "detail": f"{field} is missing"}
        for field in REQUIRED_FIELDS
        if not record.get(field) and not (field == "date" and record.get("date_unparsed"))
    ]


def consistency(record: dict, timestamp: str | None) -> list[dict]:
    """Values that are present have a valid form."""
    problems = []
    if record.get("date_unparsed"):
        problems.append({"code": BAD_DATE, "field": "date", "detail": f"cannot parse '{record['date_unparsed']}' as a date"})
    elif record.get("date") and timestamp and record["date"] > timestamp[:10]:
        # ISO dates compare correctly as strings.
        problems.append({"code": BAD_DATE, "field": "date", "detail": f"work date {record['date']} is after the entry was logged ({timestamp[:10]})"})
    if record.get("equipment_id") and not EQUIPMENT_ID_RE.match(record["equipment_id"]):
        problems.append({"code": BAD_EQUIPMENT_ID, "field": "equipment_id", "detail": f"'{record['equipment_id']}' does not match FAMILY-NN"})
    if record.get("fault_code") and not FAULT_CODE_RE.match(record["fault_code"]):
        problems.append({"code": BAD_FAULT_CODE, "field": "fault_code", "detail": f"'{record['fault_code']}' does not match FLT-NNNN"})
    if record.get("resolution_status") and record["resolution_status"] not in RESOLUTION_STATUSES:
        problems.append({"code": BAD_ENUM, "field": "resolution_status", "detail": f"'{record['resolution_status']}' is not a known status"})
    if record.get("action_category") and record["action_category"] not in ACTION_CATEGORIES:
        problems.append({"code": BAD_ENUM, "field": "action_category", "detail": f"'{record['action_category']}' is not a known category"})
    return problems


def check(record: dict, timestamp: str | None) -> list[dict]:
    return completeness(record) + consistency(record, timestamp)
