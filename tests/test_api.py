"""API contract tests. The pipeline is replaced by a fake, so these run
offline: no model server, no index."""

import pytest
from fastapi.testclient import TestClient

from app.api.main import app, get_service


class FakeService:
    def answer(self, question: str) -> dict:
        return {
            "answer": "Torque the liner retainer nut to 1350 Nm [1].",
            "sources": [
                {"ref": 1, "document": "drilling_equipment_reference_guide.md",
                 "chunk_id": "drilling_equipment_reference_guide.md#09", "score": 0.67},
            ],
            "confidence": {"level": "high", "note": "Answer cites 1 passage(s); best match similarity 0.67."},
            "retrieved": [],
        }

    def health(self) -> dict:
        return {"documents_indexed": 12, "chunks_indexed": 99, "llm_reachable": True, "embedder_reachable": True}


@pytest.fixture
def client():
    app.dependency_overrides[get_service] = FakeService
    # Not used as a context manager, so the startup index build does not run.
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_ask_response_schema(client):
    response = client.post("/ask", json={"question": "What torque for the liner retainer nut?"})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"answer", "sources", "confidence", "needs_human_review"}
    assert isinstance(body["answer"], str) and body["answer"]
    assert body["sources"], "an answer must carry at least one source"
    for source in body["sources"]:
        assert set(source) == {"document", "chunk_id", "score"}
        assert source["chunk_id"].startswith(source["document"])
    assert body["confidence"]["level"] in {"high", "medium", "low"}
    assert isinstance(body["confidence"]["note"], str)
    assert body["needs_human_review"] is False

    # A body without a question is rejected before reaching the pipeline.
    assert client.post("/ask", json={}).status_code == 422


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "documents_indexed": 12,
        "chunks_indexed": 99,
        "llm_reachable": True,
        "embedder_reachable": True,
    }
