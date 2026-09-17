"""Integration-style tests for offline document indexing."""

from pathlib import Path

import pytest

from app.chunking import chunk_document
from app.document_loader import load_document
from app.embeddings import EmbeddingError, build_embedding_text
from app.ingestion import ingest_document
from app.vector_store import ChromaVectorStore


class FakeEmbeddingService:
    model = "synthetic-embedding-model"

    def __init__(self) -> None:
        self.inputs: list[str] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.inputs = list(texts)
        return [
            [float(index + 1), float(len(text)), 1.0]
            for index, text in enumerate(texts)
        ]


class FailingEmbeddingService:
    model = "synthetic-embedding-model"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingError("Synthetic embedding failure.")


def test_ingestion_persists_real_loader_and_chunker_output(tmp_path: Path) -> None:
    document_path = tmp_path / "synthetic.md"
    document_path.write_text(
        "Synthetic preface.\n\n"
        "# Synthetic Alpha\n\nOriginal alpha text.\n\n"
        "## Synthetic Beta\n\nOriginal beta text.",
        encoding="utf-8",
    )
    embedding_service = FakeEmbeddingService()
    store = ChromaVectorStore(
        path=tmp_path / "chroma",
        collection_name="ingestion_collection",
    )
    expected_chunks = chunk_document(load_document(document_path))

    result = ingest_document(
        document_path,
        embedding_service=embedding_service,
        vector_store=store,
    )

    assert result.source == "synthetic.md"
    assert result.chunks_indexed == len(expected_chunks)
    assert result.collection_name == "ingestion_collection"
    assert store.count() == len(expected_chunks)
    assert embedding_service.inputs == [
        build_embedding_text(chunk) for chunk in expected_chunks
    ]

    records = store.get_all()
    assert set(records["ids"]) == {chunk.chunk_id for chunk in expected_chunks}
    positions = {chunk_id: index for index, chunk_id in enumerate(records["ids"])}

    for chunk in expected_chunks:
        position = positions[chunk.chunk_id]
        assert records["documents"][position] == chunk.text
        assert records["metadatas"][position]["source"] == chunk.source
        assert records["metadatas"][position]["token_count"] == chunk.token_count
        if chunk.section is None:
            assert "section" not in records["metadatas"][position]
        else:
            assert records["metadatas"][position]["section"] == chunk.section


def test_reingesting_shorter_document_removes_stale_chunks(tmp_path: Path) -> None:
    first_path = tmp_path / "first.md"
    first_path.write_text(
        "# One\n\nSynthetic one.\n\n"
        "# Two\n\nSynthetic two.\n\n"
        "# Three\n\nSynthetic three.",
        encoding="utf-8",
    )
    second_path = tmp_path / "second.md"
    second_path.write_text("# One\n\nReplacement synthetic text.", encoding="utf-8")
    store = ChromaVectorStore(
        path=tmp_path / "chroma",
        collection_name="replacement_collection",
    )

    ingest_document(
        first_path,
        embedding_service=FakeEmbeddingService(),
        vector_store=store,
    )
    assert store.count() == 3

    ingest_document(
        second_path,
        embedding_service=FakeEmbeddingService(),
        vector_store=store,
    )

    assert store.count() == 1
    assert store.get_all()["ids"] == ["chunk_0001"]
    assert store.get_collection_metadata()["source"] == "second.md"


def test_embedding_failure_preserves_existing_collection(tmp_path: Path) -> None:
    existing_path = tmp_path / "existing.md"
    existing_path.write_text(
        "# Existing One\n\nSynthetic one.\n\n"
        "# Existing Two\n\nSynthetic two.",
        encoding="utf-8",
    )
    replacement_path = tmp_path / "replacement.md"
    replacement_path.write_text(
        "# Replacement\n\nReplacement synthetic text.",
        encoding="utf-8",
    )
    store = ChromaVectorStore(
        path=tmp_path / "chroma",
        collection_name="failure_collection",
    )
    ingest_document(
        existing_path,
        embedding_service=FakeEmbeddingService(),
        vector_store=store,
    )
    before = store.get_all()

    with pytest.raises(EmbeddingError, match="Synthetic embedding failure"):
        ingest_document(
            replacement_path,
            embedding_service=FailingEmbeddingService(),
            vector_store=store,
        )

    after = store.get_all()
    assert after["ids"] == before["ids"]
    assert after["documents"] == before["documents"]
    assert after["metadatas"] == before["metadatas"]
