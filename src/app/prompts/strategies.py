"""Three prompt strategies for one task: maintenance log entry -> structured record.

All three share the same field guide, so a difference in score comes from the
strategy and not from one prompt knowing more about the fields.
"""

import json
import re

from app.catalog import ACTION_CATEGORIES
from app.extraction.schema import LLM_SCHEMA
from app.llm import chat

STRATEGIES = ["zero_shot", "few_shot", "chain_of_thought"]

_CATEGORY_LINES = "\n".join(f"    - {name}: {meaning}" for name, meaning in ACTION_CATEGORIES.items())

FIELD_GUIDE = f"""Extract these fields from the maintenance log entry.

- equipment_id: the equipment tag exactly as written, e.g. MUD-PUMP-04. null if the entry gives no tag. Never correct, complete or guess a tag.
- fault_code: the fault code exactly as written, e.g. FLT-0392. null if no code is mentioned.
- fault_description: what was wrong, in a few words taken from the entry. If nothing was wrong (a routine check or test), give the reason for the work instead.
- action_taken: what the engineer did, in a few words taken from the entry.
- action_category: the one category that fits action_taken:
{_CATEGORY_LINES}
- engineer_name: the engineer's name or initials exactly as written. null if the entry is unsigned.
- date: the date of the work exactly as written in the entry. null if the entry gives no calendar date ("this shift" is not a date).
- resolution_status: one of
    - resolved: fixed, fault cleared, back in service, job closed
    - pending: temporary fix, waiting on parts, follow-up or re-check still needed
    - escalated: passed to a supervisor, the OEM or onshore engineering"""

JSON_ONLY = "Reply with one JSON object containing exactly those eight keys and nothing else."

# Hand-written for the prompt. Neither entry, tag nor engineer appears in the corpus.
EXAMPLES = [
    (
        "CENT-PUMP-02 threw FLT-0990 on 9 April 2025, mechanical seal weeping at the drive end. "
        "Seal swap carried out and pump run up, no leaks. Back in service. R. Castillo",
        {
            "equipment_id": "CENT-PUMP-02",
            "fault_code": "FLT-0990",
            "fault_description": "mechanical seal weeping at the drive end",
            "action_taken": "seal swap carried out",
            "action_category": "seal_replacement",
            "engineer_name": "R. Castillo",
            "date": "9 April 2025",
            "resolution_status": "resolved",
        },
    ),
    (
        "Noticed the desander feed line vibrating badly this shift, no code on the panel. Checked the clamps "
        "and supports, nothing loose, left as is for now. Waiting on a vibration survey before this is closed out. HB",
        {
            "equipment_id": None,
            "fault_code": None,
            "fault_description": "desander feed line vibrating badly",
            "action_taken": "checked the clamps and supports",
            "action_category": "inspection",
            "engineer_name": "HB",
            "date": None,
            "resolution_status": "pending",
        },
    ),
]

COT_INSTRUCTION = """Work through the entry before answering. Under the heading REASONING, go through the eight fields in order; for each one quote the words in the entry that support your value, or state that the entry does not give it. Then write the heading FINAL JSON followed by one JSON object containing exactly those eight keys."""


def build_messages(strategy: str, log_text: str) -> list[dict]:
    entry = f"Log entry:\n{log_text}"
    if strategy == "zero_shot":
        return [{"role": "system", "content": f"{FIELD_GUIDE}\n\n{JSON_ONLY}"}, {"role": "user", "content": entry}]
    if strategy == "few_shot":
        messages = [{"role": "system", "content": f"{FIELD_GUIDE}\n\n{JSON_ONLY}"}]
        for text, record in EXAMPLES:
            messages.append({"role": "user", "content": f"Log entry:\n{text}"})
            messages.append({"role": "assistant", "content": json.dumps(record)})
        return messages + [{"role": "user", "content": entry}]
    if strategy == "chain_of_thought":
        return [{"role": "system", "content": f"{FIELD_GUIDE}\n\n{COT_INSTRUCTION}"}, {"role": "user", "content": entry}]
    raise ValueError(f"unknown strategy: {strategy}")


def parse_output(text: str) -> dict | None:
    """Pull the last JSON object out of a free-form reply. None if there is none."""
    text = re.sub(r"```(?:json)?", "", text)
    decoder = json.JSONDecoder()
    found = None
    for match in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            found = obj
    return found


def run(strategy: str, log_text: str, constrained: bool = False) -> tuple[dict | None, str, dict]:
    """Return (record or None, raw reply, token usage).

    `constrained` turns on schema-guided decoding. It is off for the prompt
    comparison, which measures the prompts alone, and on in the pipeline."""
    if constrained and strategy == "chain_of_thought":
        raise ValueError("guided JSON leaves no room for reasoning text; use zero_shot or few_shot")
    raw, usage = chat(
        build_messages(strategy, log_text),
        max_tokens=900 if strategy == "chain_of_thought" else 350,
        json_schema=LLM_SCHEMA if constrained else None,
    )
    return parse_output(raw), raw, usage
