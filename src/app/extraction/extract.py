"""Extract one maintenance log entry into a checked record."""

from app.extraction import quality
from app.extraction.normalise import normalise
from app.prompts.strategies import run

# Few-shot scored best in the Task 3 comparison (outputs/prompt_eval.md).
STRATEGY = "few_shot"


def extract(log_text: str, timestamp: str | None) -> tuple[dict | None, list[dict]]:
    """Return (record, problems). The record is None when the LLM reply could
    not be used at all; `problems` is empty for a clean record.

    Only the free text and the entry timestamp are read. The LLM output is
    constrained to the schema, so a parse failure here means the request
    itself failed or the reply was cut off."""
    try:
        raw, _, _ = run(STRATEGY, log_text, constrained=True)
    except Exception as exc:  # network error, timeout, truncated JSON
        return None, [{"code": quality.LLM_PARSE_ERROR, "field": None, "detail": f"{type(exc).__name__}: {exc}"}]
    if raw is None:
        return None, [{"code": quality.LLM_PARSE_ERROR, "field": None, "detail": "reply was not a JSON object"}]
    record = normalise(raw, timestamp)
    return record, quality.check(record, timestamp, log_text)
