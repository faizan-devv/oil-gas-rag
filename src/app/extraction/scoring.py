"""Score an extracted record against its gold record. Used by Task 2 and Task 3."""

import re

from app.extraction.schema import LAB_FIELDS

_STOPWORDS = {"the", "a", "an", "of", "on", "at", "in", "to", "with", "and", "was", "is", "were", "due", "beyond"}


def _content_words(text: str | None) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    # Crude stemming so "leaking"/"leak" and "pads"/"pad" count as the same word.
    return {re.sub(r"(ing|ed|s)$", "", w) for w in words if w not in _STOPWORDS}


def score_record(predicted: dict | None, gold: dict) -> dict[str, float]:
    """One score per lab field.

    - equipment_id, fault_code, engineer_name, date, resolution_status: 1 for an
      exact match (null matching null counts), else 0.
    - action_taken: scored on the normalised action_category, 1 or 0. This is
      the "consistent normalised value" the lab asks for.
    - fault_description: free text, so scored on how many of the gold
      description's content words it keeps: 1 for at least 60%, 0.5 for at
      least 30%, else 0.
    An unparseable reply (predicted is None) scores 0 on every field."""
    if predicted is None:
        return {field: 0.0 for field in LAB_FIELDS}
    scores = {}
    for field in ("equipment_id", "fault_code", "engineer_name", "date", "resolution_status"):
        scores[field] = float(predicted.get(field) == gold.get(field))
    scores["action_taken"] = float(predicted.get("action_category") == gold.get("action_category"))
    gold_words = _content_words(gold.get("fault_description"))
    kept = len(gold_words & _content_words(predicted.get("fault_description"))) / max(len(gold_words), 1)
    scores["fault_description"] = 1.0 if kept >= 0.6 else 0.5 if kept >= 0.3 else 0.0
    return {field: scores[field] for field in LAB_FIELDS}
