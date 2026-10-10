"""FastAPI wrapper around the RAG pipeline.

    uv run uvicorn app.api.main:app --port 8000
"""

import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import llm
from app.rag import pipeline, store

log = logging.getLogger("uvicorn.error")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class Source(BaseModel):
    document: str
    chunk_id: str
    score: float


class Confidence(BaseModel):
    level: Literal["high", "medium", "low"]
    note: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    confidence: Confidence
    # True for low confidence: the hook a review queue would consume.
    needs_human_review: bool


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    documents_indexed: int
    chunks_indexed: int
    llm_reachable: bool
    embedder_reachable: bool


class RagService:
    """The seam between HTTP and the pipeline; tests replace it with a fake."""

    def answer(self, question: str) -> dict:
        store.build_index()  # no-op once built; covers a start-up with the embedder down
        return pipeline.answer(question)

    def health(self) -> dict:
        try:
            counts = store.stats()
        except Exception:  # index directory missing or unreadable
            counts = {"documents_indexed": 0, "chunks_indexed": 0}
        return counts | {"llm_reachable": llm.llm_reachable(), "embedder_reachable": llm.embedder_reachable()}


def get_service() -> RagService:
    return RagService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build the index on first start. The reachability probe has a 3 s timeout,
    # so an unreachable embedding server cannot stall start-up: the API comes
    # up, /health reports "degraded", and the first /ask retries the build.
    if not llm.embedder_reachable():
        log.error("embedding server unreachable at start-up; index not built yet")
    else:
        try:
            log.info("index ready: %s", store.build_index())
        except Exception as exc:
            log.error("could not build the index at start-up: %s", exc)
    yield


app = FastAPI(title="Field document Q&A", version="0.1.0", lifespan=lifespan)


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, service: RagService = Depends(get_service)) -> AskResponse:
    try:
        result = service.answer(request.question)
    except Exception as exc:
        log.exception("ask failed")
        raise HTTPException(status_code=503, detail=f"model or index unavailable: {type(exc).__name__}") from exc
    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
        confidence=result["confidence"],
        needs_human_review=result["confidence"]["level"] == "low",
    )


@app.get("/health", response_model=HealthResponse)
def health(service: RagService = Depends(get_service)) -> HealthResponse:
    state = service.health()
    healthy = state["llm_reachable"] and state["embedder_reachable"] and state["documents_indexed"] > 0
    return HealthResponse(status="ok" if healthy else "degraded", **state)
