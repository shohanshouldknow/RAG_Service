"""Tests for persistent Chroma chunk storage."""

from pathlib import Path

import pytest
import chromadb

from app.chunking import DocumentChunk
from app.vector_store import ChromaVectorStore, VectorStoreError


def _synthetic_chunks() -> list[DocumentChunk]:
    return [
        DocumentChunk(
            chunk_id="chunk_0001",
            source="synthetic.md",
            section="Synthetic Section",
            text="First original chunk.",
            token_count=4,
        ),
        DocumentChunk(
            chunk_id="chunk_0002",
            source="synthetic.md",
            section=None,
            text="Second original chunk.",
            token_count=4,
        ),
    ]


def test_records_and_embeddings_persist_across_store_instances(tmp_path: Path) -> None:
    path = tmp_path / "chroma"
    chunks = _synthetic_chunks()
    embeddings = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    store = ChromaVectorStore(path=path, collection_name="test_collection")

    store.replace_chunks(chunks, embeddings, embedding_model="synthetic-model")

    assert store.count() == 2
    records = store.get_all()
    assert set(records["ids"]) == {"chunk_0001", "chunk_0002"}

    positions = {chunk_id: index for index, chunk_id in enumerate(records["ids"])}
    first = positions["chunk_0001"]
    second = positions["chunk_0002"]

    assert records["documents"][first] == "First original chunk."
    assert records["documents"][second] == "Second original chunk."
    assert records["metadatas"][first] == {
        "source": "synthetic.md",
        "section": "Synthetic Section",
        "token_count": 4,
    }
    assert records["metadatas"][second] == {
        "source": "synthetic.md",
        "token_count": 4,
    }
    assert list(records["embeddings"][first]) == pytest.approx(embeddings[0])
    assert list(records["embeddings"][second]) == pytest.approx(embeddings[1])

    reopened = ChromaVectorStore(path=path, collection_name="test_collection")
    assert reopened.count() == 2
    assert set(reopened.get_all()["ids"]) == {"chunk_0001", "chunk_0002"}
    assert reopened.get_collection_metadata() == {
        "embedding_model": "synthetic-model",
        "source": "synthetic.md",
    }


def test_collection_uses_public_cosine_distance_configuration(tmp_path: Path) -> None:
    store = ChromaVectorStore(
        path=tmp_path / "chroma",
        collection_name="cosine_collection",
    )
    store.replace_chunks(
        _synthetic_chunks(),
        [[1.0, 0.0], [0.0, 1.0]],
        embedding_model="synthetic-model",
    )

    configuration = store.get_collection_configuration()

    assert configuration["hnsw"]["space"] == "cosine"
    assert configuration["embedding_function"] is None


def test_known_vectors_verify_cosine_distance_and_similarity(tmp_path: Path) -> None:
    chunks = [
        DocumentChunk(
            chunk_id="same",
            source="synthetic.md",
            section=None,
            text="Same direction.",
            token_count=3,
        ),
        DocumentChunk(
            chunk_id="orthogonal",
            source="synthetic.md",
            section=None,
            text="Orthogonal direction.",
            token_count=3,
        ),
        DocumentChunk(
            chunk_id="opposite",
            source="synthetic.md",
            section=None,
            text="Opposite direction.",
            token_count=3,
        ),
    ]
    store = ChromaVectorStore(
        path=tmp_path / "chroma",
        collection_name="distance_collection",
    )
    store.replace_chunks(
        chunks,
        [[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]],
        embedding_model="synthetic-model",
    )

    results = store.search([1.0, 0.0], limit=3)

    assert [result.chunk_id for result in results] == [
        "same",
        "orthogonal",
        "opposite",
    ]
    assert [result.distance for result in results] == pytest.approx(
        [0.0, 1.0, 2.0], abs=1e-6
    )
    assert [result.similarity for result in results] == pytest.approx(
        [1.0, 0.0, -1.0], abs=1e-6
    )
    assert results[0].text == "Same direction."
    assert results[0].metadata == {
        "source": "synthetic.md",
        "token_count": 3,
    }


def test_missing_collection_raises_clear_retrieval_error(tmp_path: Path) -> None:
    store = ChromaVectorStore(
        path=tmp_path / "chroma",
        collection_name="missing_collection",
    )

    with pytest.raises(VectorStoreError, match="does not exist"):
        store.search([1.0, 0.0], limit=1)


def test_empty_collection_raises_clear_retrieval_error(tmp_path: Path) -> None:
    path = tmp_path / "chroma"
    client = chromadb.PersistentClient(path=str(path))
    client.create_collection(
        name="empty_collection",
        configuration={"hnsw": {"space": "cosine"}},
        embedding_function=None,
    )
    store = ChromaVectorStore(path=path, collection_name="empty_collection")

    with pytest.raises(VectorStoreError, match="is empty"):
        store.search([1.0, 0.0], limit=1)
