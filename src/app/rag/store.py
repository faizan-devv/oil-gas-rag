"""Chroma vector store: build, count and query."""

import re
from functools import lru_cache

import chromadb
import numpy as np
from chromadb.config import Settings as ChromaSettings
from rank_bm25 import BM25Okapi

from app.config import get_settings
from app.llm import embed
from app.rag.chunking import Chunk, chunk_documents
from app.rag.loaders import load_documents

COLLECTION = "corpus"
CANDIDATES = 20  # how deep each ranking goes before fusion
RRF_K = 60  # standard reciprocal-rank-fusion constant

_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def _collection(reset: bool = False):
    client = chromadb.PersistentClient(
        path=str(get_settings().index_dir),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    if reset:
        try:
            client.delete_collection(COLLECTION)
        except Exception:  # collection did not exist yet
            pass
    # bge-m3 vectors are compared by cosine similarity.
    return client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def build_index(force: bool = False) -> dict:
    """Embed the corpus into Chroma. A no-op when the index exists, unless forced."""
    if not force and _collection().count() > 0:
        return stats()
    chunks = chunk_documents(load_documents(get_settings().data_dir))
    collection = _collection(reset=True)
    collection.add(
        ids=[c.id for c in chunks],
        documents=[c.text for c in chunks],
        embeddings=embed([c.text for c in chunks]),
        metadatas=[{"source": c.source, "doc_type": c.doc_type, "section": c.section} for c in chunks],
    )
    _keyword_index.cache_clear()
    return stats()


def stats() -> dict:
    metadatas = _collection().get(include=["metadatas"])["metadatas"]
    return {
        "documents_indexed": len({m["source"] for m in metadatas}),
        "chunks_indexed": len(metadatas),
    }


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, keeping hyphenated IDs whole: 'MUD-PUMP-04' and
    'FLT-0392' must each stay one token or keyword search cannot tell
    MUD-PUMP-04 from MUD-PUMP-01."""
    return _TOKEN.findall(text.lower())


@lru_cache(maxsize=1)
def _keyword_index() -> tuple[list[str], BM25Okapi]:
    got = _collection().get(include=["documents"])
    return got["ids"], BM25Okapi([tokenize(doc) for doc in got["documents"]])


def search(question: str, k: int, hybrid: bool | None = None) -> list[tuple[Chunk, float]]:
    """Top-k chunks, each with its cosine similarity to the question.

    Dense-only ranks by cosine. Hybrid also ranks every chunk by BM25 and
    merges the two rankings with reciprocal rank fusion, which rescues
    exact-ID questions where sibling IDs embed almost identically."""
    hybrid = get_settings().hybrid if hybrid is None else hybrid
    collection = _collection()
    query_vector = embed([question])[0]
    dense = collection.query(query_embeddings=[query_vector], n_results=max(k, CANDIDATES), include=["distances"])
    dense_ids = dense["ids"][0]
    cosine = {id_: 1.0 - d for id_, d in zip(dense_ids, dense["distances"][0])}

    if hybrid:
        ids, bm25 = _keyword_index()
        scores = bm25.get_scores(tokenize(question))
        keyword_ids = [ids[i] for i in np.argsort(scores)[::-1][:CANDIDATES] if scores[i] > 0]
        fused: dict[str, float] = {}
        for ranking in (dense_ids, keyword_ids):
            for rank, id_ in enumerate(ranking):
                fused[id_] = fused.get(id_, 0.0) + 1.0 / (RRF_K + rank + 1)
        top_ids = sorted(fused, key=fused.get, reverse=True)[:k]
    else:
        top_ids = dense_ids[:k]

    got = collection.get(ids=top_ids, include=["documents", "metadatas", "embeddings"])
    rows = {id_: (text, meta, vec) for id_, text, meta, vec in zip(got["ids"], got["documents"], got["metadatas"], got["embeddings"])}
    results = []
    for id_ in top_ids:
        text, meta, vec = rows[id_]
        if id_ not in cosine:  # found by keyword only, outside the dense candidates
            cosine[id_] = float(np.dot(query_vector, vec) / (np.linalg.norm(query_vector) * np.linalg.norm(vec)))
        results.append((Chunk(id_, text, meta["source"], meta["doc_type"], meta["section"]), cosine[id_]))
    return results
