"""The extraction contract: what the LLM returns and what the analyst receives."""

from app.catalog import ACTION_CATEGORIES, RESOLUTION_STATUSES

# Fields the lab asks for. fault_code is the only optional one.
LAB_FIELDS = [
    "equipment_id", "fault_code", "fault_description", "action_taken",
    "engineer_name", "date", "resolution_status",
]
REQUIRED_FIELDS = [f for f in LAB_FIELDS if f != "fault_code"]

# Column order of the analyst-facing table.
OUTPUT_COLUMNS = [
    "log_id", "equipment_id", "fault_code", "fault_description", "action_taken",
    "action_category", "engineer_name", "date", "date_source", "resolution_status", "source_file",
]

_NULLABLE_STRING = {"type": ["string", "null"]}

# JSON schema handed to the server's guided decoder. Identifiers and the date
# are copied as written; validating and normalising them is done in Python,
# where a failure can be logged with a reason instead of being papered over.
LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "equipment_id": _NULLABLE_STRING,
        "fault_code": _NULLABLE_STRING,
        "fault_description": _NULLABLE_STRING,
        "action_taken": _NULLABLE_STRING,
        "action_category": {"type": "string", "enum": list(ACTION_CATEGORIES)},
        "engineer_name": _NULLABLE_STRING,
        "date": _NULLABLE_STRING,
        "resolution_status": {"type": "string", "enum": RESOLUTION_STATUSES},
    },
    "required": [
        "equipment_id", "fault_code", "fault_description", "action_taken",
        "action_category", "engineer_name", "date", "resolution_status",
    ],
    "additionalProperties": False,
}
