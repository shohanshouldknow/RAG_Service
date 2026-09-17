"""Tests for local sentence-transformer embedding generation."""

import pytest

from app.chunking import DocumentChunk
from app.config import Settings
from app.embeddings import EmbeddingError, EmbeddingService, build_embedding_text


class FakeEncoder:
    def __init__(self, vectors: list[list[float]] | None = None) -> None:
        self.vectors = vectors or []
        self.calls: list[tuple[list[str], dict[str, object]]] = []
        self.error: Exception | None = None

    def encode(self, texts: list[str], **kwargs: object) -> list[list[float]]:
        self.calls.append((texts, kwargs))
        if self.error is not None:
            raise self.error
        return self.vectors


def test_embedding_text_includes_section_context() -> None:
    chunk = DocumentChunk(
        chunk_id="chunk_0001",
        source="synthetic.md",
        section="Synthetic Section",
        text="Original synthetic text.",
        token_count=4,
    )

    embedding_text = build_embedding_text(chunk)

    assert embedding_text == "Synthetic Section\n\nOriginal synthetic text."
    assert chunk.text == "Original synthetic text."


def test_embedding_text_without_section_is_unchanged() -> None:
    chunk = DocumentChunk(
        chunk_id="chunk_0001",
        source="synthetic.txt",
        section=None,
        text="Original synthetic text.",
        token_count=4,
    )

    assert build_embedding_text(chunk) == chunk.text


def test_embed_texts_batches_locally_and_returns_plain_float_vectors() -> None:
    encoder = FakeEncoder([[1, 0], [0, 1]])
    service = EmbeddingService(
        model="configured-embedding-model",
        encoder=encoder,
        batch_size=16,
    )
    texts = ["first synthetic text", "second synthetic text"]

    embeddings = service.embed_texts(texts)

    assert embeddings == [[1.0, 0.0], [0.0, 1.0]]
    assert all(isinstance(value, float) for vector in embeddings for value in vector)
    assert encoder.calls == [
        (
            texts,
            {
                "batch_size": 16,
                "show_progress_bar": False,
                "convert_to_numpy": True,
                "normalize_embeddings": True,
            },
        )
    ]


def test_empty_input_skips_local_encoder() -> None:
    encoder = FakeEncoder()
    service = EmbeddingService(model="synthetic-model", encoder=encoder)

    assert service.embed_texts([]) == []
    assert encoder.calls == []


def test_provider_exception_becomes_clear_embedding_error() -> None:
    encoder = FakeEncoder()
    encoder.error = RuntimeError("synthetic local model failure")
    service = EmbeddingService(model="synthetic-model", encoder=encoder)

    with pytest.raises(EmbeddingError, match="embedding generation failed") as exc_info:
        service.embed_texts(["synthetic input"])

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_wrong_vector_count_is_rejected() -> None:
    service = EmbeddingService(
        model="synthetic-model",
        encoder=FakeEncoder([[1.0, 0.0]]),
    )

    with pytest.raises(EmbeddingError, match="unexpected number"):
        service.embed_texts(["first", "second"])


def test_local_provider_defaults_require_no_api_key() -> None:
    settings = Settings(_env_file=None)

    assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert settings.llm_model == "qwen2.5:3b"
    assert settings.ollama_base_url == "http://localhost:11434"
