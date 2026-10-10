"""Retrieve, answer with citations, and attach a confidence note.

    uv run python -m app.rag.pipeline "What does the manual say about replacing the mud pump seal?"
"""

import re
import sys

from app.config import get_settings
from app.llm import chat
from app.rag import store

NOT_FOUND = "Not found in the documents."

# Cosine similarity of the best cited passage (bge-m3). Set from the score
# distribution of the evaluation questions; see the README.
HIGH_SIMILARITY = 0.60
MEDIUM_SIMILARITY = 0.50

SYSTEM_PROMPT = f"""You answer questions from field engineers about wells and drilling equipment.

Rules:
- Use only the numbered passages below. Do not use outside knowledge.
- Each passage is labelled with its kind: reference manual, well report or maintenance log. If the question asks about one kind ("what does the manual say", "in the maintenance logs"), answer only from passages of that kind.
- Answer from the passage that addresses the question most directly, and give its specifics: for a procedure give the steps and values, for an event give what happened.
- After every statement, cite the passage it came from as [n], for example [2].
- Copy numbers, units, equipment IDs and fault codes exactly as they appear.
- State only what the passages state. Do not guess at causes or add interpretation.
- If the passages do not contain the answer, reply with exactly: {NOT_FOUND}
- Be concise: a short paragraph or a short list."""

DOC_KIND = {"manual": "reference manual", "well_report": "well report", "maintenance_log": "maintenance log"}

_CITATION = re.compile(r"\[(\d+)\]")


def answer(question: str, k: int | None = None) -> dict:
    """Return {"answer", "sources", "confidence", "retrieved"}.

    `sources` holds only the passages the answer cites; `retrieved` holds
    everything that was shown to the model, for auditing retrieval."""
    hits = store.search(question, k or get_settings().top_k)
    context = "\n\n".join(f"[{n}] ({DOC_KIND[chunk.doc_type]}, {chunk.id})\n{chunk.text}" for n, (chunk, _) in enumerate(hits, start=1))
    text, _ = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Passages:\n\n{context}\n\nQuestion: {question}"},
        ],
        max_tokens=500,
    )
    retrieved = [
        {"ref": n, "document": chunk.source, "chunk_id": chunk.id, "score": round(score, 3)}
        for n, (chunk, score) in enumerate(hits, start=1)
    ]
    declined = NOT_FOUND.rstrip(".").lower() in text.lower()
    cited = {int(n) for n in _CITATION.findall(text)}
    sources = [] if declined else [r for r in retrieved if r["ref"] in cited]
    return {
        "answer": NOT_FOUND if declined else text,
        "sources": sources,
        "confidence": confidence(declined, sources, retrieved),
        "retrieved": retrieved,
    }


def confidence(declined: bool, sources: list[dict], retrieved: list[dict]) -> dict:
    """A heuristic, not a calibrated probability: retrieval similarity plus
    whether the model grounded its answer."""
    top = max((r["score"] for r in retrieved), default=0.0)
    if declined:
        return {"level": "low", "note": f"The retrieved passages do not answer this question (best similarity {top:.2f})."}
    if not sources:
        return {"level": "low", "note": "The answer cites no passage, so it cannot be audited."}
    best = max(s["score"] for s in sources)
    if best >= HIGH_SIMILARITY:
        return {"level": "high", "note": f"Answer cites {len(sources)} passage(s); best match similarity {best:.2f}."}
    if best >= MEDIUM_SIMILARITY:
        return {"level": "medium", "note": f"Cited passages are a moderate match (similarity {best:.2f}); check the sources."}
    return {"level": "low", "note": f"Cited passages are a weak match (similarity {best:.2f}); treat as unverified."}


if __name__ == "__main__":
    store.build_index()
    result = answer(" ".join(sys.argv[1:]) or "What does the manual say about replacing the mud pump seal?")
    print(result["answer"], "\n")
    for s in result["sources"]:
        print(f"  [{s['ref']}] {s['chunk_id']}  (similarity {s['score']})")
    print(f"\nconfidence: {result['confidence']['level']} - {result['confidence']['note']}")
