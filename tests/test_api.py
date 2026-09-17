"""Integration tests for health and grounded query API behavior."""

import pytest
from fastapi.testclient import TestClient

from app.config import ConfigurationError
from app.constants import INSUFFICIENT_DOCUMENTATION_MESSAGE
from app.dependencies import get_rag_service
from app.embeddings import EmbeddingError
from app.llm import LLMError
from app.main import app
from app.rag import RAGResult
from app.schemas import MAX_QUESTION_LENGTH
from app.vector_store import RetrievedChunk, VectorStoreError


class FakeRAGService:
    def __init__(
        self,
        result: RAGResult | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.questions: list[str] = []

    def answer(self, question: str) -> RAGResult:
        self.questions.append(question)
        if self.error is not None:
            raise self.error
        if self.result is None:
            raise RuntimeError("Synthetic test result was not configured.")
        return self.result


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides.clear()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _override_rag(fake: FakeRAGService) -> None:
    app.dependency_overrides[get_rag_service] = lambda: fake


def _source() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chunk_0004",
        text="Synthetic retention evidence.",
        metadata={"source": "synthetic.md", "token_count": 4},
        distance=0.11,
        similarity=0.89,
    )


def test_health_returns_http_200(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200


def test_health_returns_exact_response(client: TestClient) -> None:
    response = client.get("/health")

    assert response.json() == {"status": "ok"}


def test_health_does_not_require_external_configuration(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("MIN_SIMILARITY", raising=False)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_supported_query_returns_mapped_sources_and_tokens(
    client: TestClient,
) -> None:
    fake = FakeRAGService(
        RAGResult(
            answer="Synthetic backups are retained for 30 days.",
            sources=[_source()],
            tokens_used=164,
        )
    )
    _override_rag(fake)

    response = client.post(
        "/api/query",
        json={"question": "  What is the synthetic retention policy?  "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Synthetic backups are retained for 30 days.",
        "sources": [
            {
                "chunk_id": "chunk_0004",
                "similarity_score": 0.89,
                "text_snippet": "Synthetic retention evidence.",
            }
        ],
        "tokens_used": 164,
    }
    assert fake.questions == ["What is the synthetic retention policy?"]
    assert "distance" not in response.text


def test_fallback_query_returns_http_200_without_sources(
    client: TestClient,
) -> None:
    fake = FakeRAGService(
        RAGResult(
            answer=INSUFFICIENT_DOCUMENTATION_MESSAGE,
            sources=[],
            tokens_used=19,
        )
    )
    _override_rag(fake)

    response = client.post(
        "/api/query",
        json={"question": "Unsupported synthetic question?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": INSUFFICIENT_DOCUMENTATION_MESSAGE,
        "sources": [],
        "tokens_used": 19,
    }


@pytest.mark.parametrize(
    "question",
    ["", "   \t\n", "x" * (MAX_QUESTION_LENGTH + 1)],
    ids=["empty", "whitespace-only", "too-long"],
)
def test_invalid_questions_return_422(
    question: str,
    client: TestClient,
) -> None:
    fake = FakeRAGService(
        RAGResult(answer="Unused.", sources=[], tokens_used=0)
    )
    _override_rag(fake)

    response = client.post("/api/query", json={"question": question})

    assert response.status_code == 422
    assert fake.questions == []


def test_missing_query_configuration_returns_503(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.delenv("MIN_SIMILARITY", raising=False)

    response = client.post(
        "/api/query",
        json={"question": "Synthetic configured question?"},
    )

    assert response.status_code == 503
    assert "MIN_SIMILARITY" in response.json()["detail"]
    assert INSUFFICIENT_DOCUMENTATION_MESSAGE not in response.text


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (
            ConfigurationError("Synthetic missing configuration."),
            503,
            "Synthetic missing configuration.",
        ),
        (
            VectorStoreError("C:/private/path/index failure"),
            503,
            "Document index is unavailable or incompatible.",
        ),
        (
            EmbeddingError("sensitive embedding provider body"),
            502,
            "AI provider request failed.",
        ),
        (
            LLMError("sensitive LLM provider body"),
            502,
            "AI provider request failed.",
        ),
        (
            RuntimeError("sensitive unexpected details"),
            500,
            "Internal server error.",
        ),
    ],
)
def test_technical_failures_are_http_errors_not_fallbacks(
    error: Exception,
    expected_status: int,
    expected_detail: str,
    client: TestClient,
) -> None:
    _override_rag(FakeRAGService(error=error))

    response = client.post(
        "/api/query",
        json={"question": "Synthetic technical failure?"},
    )

    assert response.status_code == expected_status
    assert expected_detail in response.json()["detail"]
    assert INSUFFICIENT_DOCUMENTATION_MESSAGE not in response.text
    assert "sensitive" not in response.text
    assert "private/path" not in response.text
