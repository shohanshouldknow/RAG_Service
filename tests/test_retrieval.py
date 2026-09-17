"""Tests for question retrieval and evidence filtering."""

from pathlib import Path

import pytest

from app.chunking import DocumentChunk
from app.config import ConfigurationError, Settings
from app.retrieval import RetrievalService
from app.vector_store import ChromaVectorStore, RetrievedChunk, VectorStoreError


class FakeEmbeddingService:
    model = "synthetic-model"

    def __init__(self) -> None:
        self.inputs: list[str] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.inputs = list(texts)
        return [[1.0, 0.0] for _ in texts]


class FakeVectorStore:
    def __init__(
        self,
        results: list[RetrievedChunk],
        *,
        embedding_model: str = "synthetic-model",
    ) -> None:
        self.results = results
        self.embedding_model = embedding_model
        self.calls: list[tuple[list[float], int]] = []

    def validate_embedding_model(self, expected_model: str) -> None:
        if expected_model != self.embedding_model:
            raise VectorStoreError("Synthetic embedding model mismatch.")

    def search(
        self,
        query_embedding: list[float],
        *,
        limit: int,
    ) -> list[RetrievedChunk]:
        self.calls.append((list(query_embedding), limit))
        return self.results[:limit]


def _result(chunk_id: str, similarity: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=f"Synthetic text for {chunk_id}.",
        metadata={"source": "synthetic.md", "token_count": 5},
        distance=1.0 - similarity,
        similarity=similarity,
    )


def test_retrieval_embeds_question_and_returns_only_qualifying_chunks() -> None:
    embeddings = FakeEmbeddingService()
    store = FakeVectorStore(
        [_result("high", 0.8), _result("boundary", 0.6), _result("low", 0.2)]
    )
    service = RetrievalService(
        embedding_service=embeddings,
        vector_store=store,
        top_k=3,
        min_similarity=0.6,
    )

    results = service.retrieve("  synthetic question?  ")

    assert embeddings.inputs == ["synthetic question?"]
    assert store.calls == [([1.0, 0.0], 3)]
    assert [result.chunk_id for result in results] == ["high", "boundary"]
    assert results[0].distance == pytest.approx(0.2)
    assert results[0].similarity == pytest.approx(0.8)


def test_low_confidence_retrieval_returns_no_qualifying_chunks() -> None:
    service = RetrievalService(
        embedding_service=FakeEmbeddingService(),
        vector_store=FakeVectorStore([_result("low", 0.49)]),
        top_k=4,
        min_similarity=0.5,
    )

    assert service.retrieve("synthetic question") == []


def test_fake_question_embedding_retrieves_from_real_chroma(tmp_path: Path) -> None:
    chunks = [
        DocumentChunk(
            chunk_id="matching",
            source="synthetic.md",
            section="Matching",
            text="Matching synthetic evidence.",
            token_count=4,
        ),
        DocumentChunk(
            chunk_id="unrelated",
            source="synthetic.md",
            section="Unrelated",
            text="Unrelated synthetic evidence.",
            token_count=4,
        ),
    ]
    store = ChromaVectorStore(
        path=tmp_path / "chroma",
        collection_name="retrieval_integration",
    )
    store.replace_chunks(
        chunks,
        [[1.0, 0.0], [0.0, 1.0]],
        embedding_model="synthetic-model",
    )
    embeddings = FakeEmbeddingService()
    service = RetrievalService(
        embedding_service=embeddings,
        vector_store=store,
        top_k=2,
        min_similarity=0.5,
    )

    results = service.retrieve("Which evidence matches?")

    assert embeddings.inputs == ["Which evidence matches?"]
    assert [result.chunk_id for result in results] == ["matching"]
    assert results[0].text == "Matching synthetic evidence."
    assert results[0].metadata["section"] == "Matching"
    assert results[0].distance == pytest.approx(0.0, abs=1e-6)
    assert results[0].similarity == pytest.approx(1.0, abs=1e-6)


def test_embedding_model_mismatch_requires_reingestion(tmp_path: Path) -> None:
    chunk = DocumentChunk(
        chunk_id="chunk_0001",
        source="synthetic.md",
        section=None,
        text="Synthetic evidence.",
        token_count=3,
    )
    store = ChromaVectorStore(
        path=tmp_path / "chroma",
        collection_name="model_mismatch",
    )
    store.replace_chunks(
        [chunk],
        [[1.0, 0.0]],
        embedding_model="indexed-model",
    )
    embeddings = FakeEmbeddingService()
    service = RetrievalService(
        embedding_service=embeddings,
        vector_store=store,
        top_k=1,
        min_similarity=0.5,
    )

    with pytest.raises(VectorStoreError, match="Re-ingest the document"):
        service.retrieve("Synthetic question")

    assert embeddings.inputs == []


def test_empty_question_is_rejected_before_embedding() -> None:
    embeddings = FakeEmbeddingService()
    service = RetrievalService(
        embedding_service=embeddings,
        vector_store=FakeVectorStore([]),
        top_k=4,
        min_similarity=0.5,
    )

    with pytest.raises(ValueError, match="Question cannot be empty"):
        service.retrieve("   ")

    assert embeddings.inputs == []


def test_retrieval_settings_load_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TOP_K", "7")
    monkeypatch.setenv("MIN_SIMILARITY", "0.42")

    settings = Settings(_env_file=None)

    assert settings.top_k == 7
    assert settings.require_min_similarity() == pytest.approx(0.42)


def test_similarity_threshold_has_no_uncalibrated_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MIN_SIMILARITY", raising=False)
    settings = Settings(_env_file=None)

    assert settings.top_k == 4
    assert settings.min_similarity is None
    with pytest.raises(ConfigurationError, match="must be configured after calibration"):
        settings.require_min_similarity()
