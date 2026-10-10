"""Task 3: compare zero-shot, few-shot and chain-of-thought prompts on extraction.

Each strategy is run on five test entries with schema-guided decoding OFF, so
the score reflects the prompt alone. The same three prompts are then run over
every entry in the corpus as a larger sanity check on the five-entry result.

    uv run python -m app.prompts.run_eval
"""

import json
from concurrent.futures import ThreadPoolExecutor

from app.config import get_settings
from app.extraction.normalise import normalise
from app.extraction.schema import LAB_FIELDS
from app.extraction.scoring import score_record
from app.prompts.strategies import STRATEGIES, run

# Five entries chosen for the cases that make extraction hard.
TEST_INPUTS = {
    "LOG-0003": "note form, dd/mm/yyyy date, initials only, escalated",
    "LOG-0011": "no equipment tag in the text (must return null, not guess one)",
    "LOG-0016": "'annular element' swap must map to seal_replacement; US-style date",
    "LOG-0028": "no fault code, initials only, ungrammatical action phrase",
    "LOG-0029": "no calendar date ('this shift'), so the date must be null",
}


def evaluate(strategy: str, gold: dict) -> dict:
    record, raw, usage = run(strategy, gold["log_text"], constrained=False)
    predicted = normalise(record, gold["timestamp"]) if record is not None else None
    scores = score_record(predicted, gold)
    return {
        "log_id": gold["log_id"],
        "strategy": strategy,
        "valid_json": record is not None,
        "scores": scores,
        "total": sum(scores.values()),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "predicted": predicted,
        "raw_output": raw,
    }


def run_all(golds: list[dict]) -> list[dict]:
    jobs = [(s, g) for s in STRATEGIES for g in golds]
    with ThreadPoolExecutor(8) as pool:
        return list(pool.map(lambda job: evaluate(*job), jobs))


def summary_table(results: list[dict], n: int) -> str:
    lines = [
        "| Strategy | Total score | " + " | ".join(LAB_FIELDS) + " | Valid JSON | Avg prompt tokens | Avg output tokens |",
        "|---|---|" + "---|" * (len(LAB_FIELDS) + 3),
    ]
    for strategy in STRATEGIES:
        rows = [r for r in results if r["strategy"] == strategy]
        total = sum(r["total"] for r in rows)
        per_field = [f"{sum(r['scores'][f] for r in rows):g}/{n}" for f in LAB_FIELDS]
        lines.append(
            f"| {strategy} | **{total:g}/{n * len(LAB_FIELDS)}** | " + " | ".join(per_field)
            + f" | {sum(r['valid_json'] for r in rows)}/{n}"
            + f" | {sum(r['prompt_tokens'] for r in rows) / n:.0f}"
            + f" | {sum(r['completion_tokens'] for r in rows) / n:.0f} |"
        )
    return "\n".join(lines)


def main() -> None:
    settings = get_settings()
    gold = {}
    for line in (settings.gold_dir / "maintenance_logs.jsonl").read_text().splitlines():
        row = json.loads(line)
        gold[row["log_id"]] = row

    test = run_all([gold[i] for i in TEST_INPUTS])
    full = run_all(list(gold.values()))

    per_input = ["| Input | Why it is hard | " + " | ".join(STRATEGIES) + " |", "|---|---|" + "---|" * len(STRATEGIES)]
    for log_id, why in TEST_INPUTS.items():
        cells = []
        for strategy in STRATEGIES:
            r = next(x for x in test if x["log_id"] == log_id and x["strategy"] == strategy)
            wrong = [f for f, s in r["scores"].items() if s < 1]
            cells.append(f"{r['total']:g}/{len(LAB_FIELDS)}" + (f" (lost: {', '.join(wrong)})" if wrong else ""))
        per_input.append(f"| {log_id} | {why} | " + " | ".join(cells) + " |")

    outputs = []
    for log_id in TEST_INPUTS:
        outputs.append(f"### {log_id}\n\n**Input:** {gold[log_id]['log_text']}\n")
        expected = {f: gold[log_id][f] for f in LAB_FIELDS} | {"action_category": gold[log_id]["action_category"]}
        outputs.append(f"**Expected:** `{json.dumps(expected)}`\n")
        for strategy in STRATEGIES:
            r = next(x for x in test if x["log_id"] == log_id and x["strategy"] == strategy)
            outputs.append(f"**{strategy}** ({r['total']:g}/{len(LAB_FIELDS)}):\n\n```\n{r['raw_output']}\n```\n")

    report = "\n\n".join(
        [
            "# Prompt strategy comparison (Task 3, Option A)",
            f"## Five test inputs\n\n{summary_table(test, len(TEST_INPUTS))}",
            "### Score per input\n\n" + "\n".join(per_input),
            f"## Sanity check: all {len(gold)} corpus entries\n\n{summary_table(full, len(gold))}",
            "## Test inputs and raw outputs\n\n" + "\n".join(outputs),
        ]
    )
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    (settings.output_dir / "prompt_eval.md").write_text(report + "\n")
    with (settings.output_dir / "prompt_eval_raw.jsonl").open("w") as f:
        f.writelines(json.dumps(r | {"set": name}) + "\n" for name, rs in (("test", test), ("full", full)) for r in rs)

    print(summary_table(test, len(TEST_INPUTS)), "\n")
    print("\n".join(per_input), "\n")
    print(summary_table(full, len(gold)))


if __name__ == "__main__":
    main()
