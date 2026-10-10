"""Run the RAG test questions and write outputs/rag_eval.md.

Each question has a known answer taken from data/gold/. The script records
where the expected chunk ranks under dense-only and hybrid retrieval, and
whether the answer contains the expected facts and nothing ungrounded. The
judgement notes in the README were written by reading these outputs.

    uv run python scripts/eval_rag.py
"""

import re

from app.config import get_settings
from app.rag import pipeline, store

K = get_settings().top_k
LOGS = "maintenance_log_2025-01.jsonl"
MANUAL = "drilling_equipment_reference_guide.md"

# expected_chunks: every listed chunk should be retrieved (all are needed for
# the aggregation question). expected_facts: strings a correct answer contains.
QUESTIONS = [
    {
        "id": "Q1",
        "type": "well report (txt)",
        "question": "What were the issues during completion of WELL-2847-NX?",
        "expected_chunks": ["WELL-2847-NX.txt#03"],
        "expected_facts": ["1256", "1360", "34 bbl", "MUD-PUMP-04", "FLT-0392", "8"],
    },
    {
        "id": "Q2",
        "type": "manual",
        "question": "What does the manual say about replacing the mud pump seal?",
        "expected_chunks": [f"{MANUAL}#09"],
        "expected_facts": ["1350 Nm", "40 strokes per minute", "15 minutes", "pressure side"],
    },
    {
        "id": "Q3",
        "type": "maintenance log, exact ID",
        "question": "What happened to MUD-PUMP-04 in the maintenance logs?",
        "expected_chunks": [f"{LOGS}#LOG-0036"],
        "expected_facts": ["FLT-0392", "seal"],
    },
    {
        "id": "Q4",
        "type": "well report (PDF)",
        "question": "Why was WELL-1975-NW only partially completed?",
        "expected_chunks": ["WELL-1975-NW.pdf#01"],
        "expected_facts": ["upper zone", "bridge plug", "3785"],
    },
    {
        "id": "Q5",
        "type": "aggregation across reports",
        "question": "Which wells had H2S detected during clean-up?",
        "expected_chunks": ["WELL-1402-SE.txt#03", "WELL-2261-SX.txt#03", "WELL-4033-NW.txt#03", "WELL-4406-EA.txt#03"],
        "expected_facts": ["1402", "2261", "4033", "4406"],
    },
    {
        "id": "N1",
        "type": "negative control (not in corpus)",
        "question": "What is the daily production rate of WELL-2847-NX in barrels?",
        "expected_chunks": [],
        "expected_facts": [pipeline.NOT_FOUND],
    },
]


def ranks(question: str, expected: list[str], hybrid: bool) -> str:
    ids = [chunk.id for chunk, _ in store.search(question, K, hybrid=hybrid)]
    if not expected:
        return "n/a"
    found = [str(ids.index(e) + 1) if e in ids else "miss" for e in expected]
    return ", ".join(found)


def ungrounded_numbers(answer: str, question: str, passages: str) -> list[str]:
    """Numbers in the answer that appear in neither the cited passages nor the
    question: a cheap check for invented values."""
    body = re.sub(r"\[\d+\]", "", answer)
    allowed = passages + " " + question
    return sorted({n for n in re.findall(r"\d+(?:\.\d+)?", body) if n not in allowed})


def main() -> None:
    store.build_index()
    rows, details = [], []
    for q in QUESTIONS:
        result = pipeline.answer(q["question"])
        texts = {chunk.id: chunk.text for chunk, _ in store.search(q["question"], K)}
        cited_ids = [s["chunk_id"] for s in result["sources"]]
        cited_text = " ".join(texts[i] for i in cited_ids)
        facts_missing = [f for f in q["expected_facts"] if f.lower() not in result["answer"].lower()]
        invented = ungrounded_numbers(result["answer"], q["question"], cited_text)
        cited_expected = sum(e in cited_ids for e in q["expected_chunks"])
        rows.append(
            f"| {q['id']} | {q['type']} | {q['question']} "
            f"| {ranks(q['question'], q['expected_chunks'], hybrid=False)} "
            f"| {ranks(q['question'], q['expected_chunks'], hybrid=True)} "
            f"| {cited_expected}/{len(q['expected_chunks'])} "
            f"| {len(q['expected_facts']) - len(facts_missing)}/{len(q['expected_facts'])} "
            f"| {', '.join(invented) or 'none'} "
            f"| {result['confidence']['level']} |"
        )
        details.append(
            f"### {q['id']}: {q['question']}\n\n"
            f"**Answer:** {result['answer']}\n\n"
            f"**Cited:** {', '.join(f'[{s['ref']}] {s['chunk_id']} ({s['score']})' for s in result['sources']) or 'none'}\n\n"
            f"**Retrieved (hybrid, top {K}):** {', '.join(f'{r['chunk_id']} ({r['score']})' for r in result['retrieved'])}\n\n"
            f"**Expected facts missing from the answer:** {', '.join(facts_missing) or 'none'}\n\n"
            f"**Confidence:** {result['confidence']['level']}: {result['confidence']['note']}\n"
        )
    header = (
        f"| # | Type | Question | Rank of expected chunk, dense (top {K}) | Rank, hybrid (top {K}) "
        "| Expected chunks cited | Expected facts in answer | Numbers not in cited passages | Confidence |\n"
        "|---|---|---|---|---|---|---|---|---|"
    )
    out = get_settings().output_dir / "rag_eval.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# RAG evaluation\n\n" + header + "\n" + "\n".join(rows) + "\n\n## Full outputs\n\n" + "\n".join(details))
    print(header + "\n" + "\n".join(rows))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
