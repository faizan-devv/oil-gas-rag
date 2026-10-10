"""Task 2: maintenance logs -> clean table + quarantine file + accuracy report.

    uv run python -m app.extraction.run

Writes to outputs/:
    records.csv            clean records, one row per log entry
    maintenance.db         the same rows in SQLite, table maintenance_records
    quarantine.jsonl       failed records, each with reason codes
    extraction_report.md   accuracy against data/gold/ and quarantine results
"""

import json
import sqlite3
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from app.config import get_settings
from app.extraction.extract import STRATEGY, extract
from app.extraction.schema import LAB_FIELDS, OUTPUT_COLUMNS
from app.extraction.scoring import score_record

WORKERS = 8


def load_entries() -> list[dict]:
    entries = []
    for path in sorted((get_settings().data_dir / "maintenance_logs").glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                entries.append(json.loads(line) | {"source_file": path.name})
    return entries


def process(entry: dict) -> dict:
    record, problems = extract(entry["log_text"], entry.get("timestamp"))
    return {"entry": entry, "record": record, "problems": problems}


def write_outputs(results: list[dict]) -> tuple[pd.DataFrame, list[dict]]:
    out = get_settings().output_dir
    out.mkdir(parents=True, exist_ok=True)
    clean, quarantined = [], []
    for r in results:
        entry, record = r["entry"], r["record"]
        if r["problems"]:
            quarantined.append(
                {
                    "log_id": entry["log_id"],
                    "source_file": entry["source_file"],
                    "reason_codes": sorted({p["code"] for p in r["problems"]}),
                    "reasons": r["problems"],
                    "log_text": entry["log_text"],
                    "timestamp": entry.get("timestamp"),
                    "extracted": record,
                }
            )
        else:
            clean.append({"log_id": entry["log_id"], "source_file": entry["source_file"]} | record)

    frame = pd.DataFrame(clean, columns=OUTPUT_COLUMNS).sort_values("log_id")
    frame.to_csv(out / "records.csv", index=False)
    with sqlite3.connect(out / "maintenance.db") as db:
        frame.to_sql("maintenance_records", db, if_exists="replace", index=False)
    with (out / "quarantine.jsonl").open("w") as f:
        f.writelines(json.dumps(q) + "\n" for q in sorted(quarantined, key=lambda q: q["log_id"]))
    return frame, quarantined


def write_report(results: list[dict], frame: pd.DataFrame, quarantined: list[dict]) -> str:
    settings = get_settings()
    gold = {}
    for line in (settings.gold_dir / "maintenance_logs.jsonl").read_text().splitlines():
        row = json.loads(line)
        gold[row["log_id"]] = row

    # Field accuracy over every entry, including the defective ones: a missing
    # tag should come back null and a mistyped code should come back as typed.
    totals: Counter = Counter()
    for r in results:
        for field, score in score_record(r["record"], gold[r["entry"]["log_id"]]).items():
            totals[field] += score
    n = len(results)
    accuracy = "\n".join(f"| {f} | {totals[f]:g}/{n} | {totals[f] / n:.0%} |" for f in LAB_FIELDS)

    quarantined_ids = {q["log_id"]: q for q in quarantined}
    defective = [g for g in gold.values() if g["defect"]]
    rows = []
    for g in sorted(defective, key=lambda g: g["log_id"]):
        q = quarantined_ids.get(g["log_id"])
        got = ", ".join(q["reason_codes"]) if q else "NOT QUARANTINED"
        verdict = "caught, expected code" if q and g["expected_reason"] in q["reason_codes"] else "caught, different code" if q else "missed"
        rows.append(f"| {g['log_id']} | {g['defect']} | {g['expected_reason']} | {got} | {verdict} |")
    false_alarms = [q for q in quarantined if not gold[q["log_id"]]["defect"]]
    false_rows = "\n".join(
        f"| {q['log_id']} | {', '.join(q['reason_codes'])} | {'; '.join(p['detail'] for p in q['reasons'])} |" for q in false_alarms
    ) or "| none | | |"

    report = f"""# Extraction report (Task 2)

Prompt strategy: `{STRATEGY}` with schema-guided decoding.

- Entries processed: {n}
- Clean records written: {len(frame)}
- Quarantined: {len(quarantined)} ({len(defective)} entries were made defective on purpose)

## Field accuracy against gold ({n} entries)

| Field | Correct | Accuracy |
|---|---|---|
{accuracy}

`action_taken` is scored on the normalised `action_category`.

## Deliberately defective entries

| Entry | Defect planted | Expected reason | Reason codes raised | Result |
|---|---|---|---|---|
{chr(10).join(rows)}

## Quarantined entries that were not defective

| Entry | Reason codes | Detail |
|---|---|---|
{false_rows}

## Reason codes in the quarantine file

{chr(10).join(f'- {code}: {count}' for code, count in sorted(Counter(c for q in quarantined for c in q['reason_codes']).items()))}
"""
    (settings.output_dir / "extraction_report.md").write_text(report)
    return report


def main() -> None:
    entries = load_entries()
    with ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(process, entries))
    frame, quarantined = write_outputs(results)
    print(write_report(results, frame, quarantined))


if __name__ == "__main__":
    main()
