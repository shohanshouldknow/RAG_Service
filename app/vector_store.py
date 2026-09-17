"""Persistent Chroma storage for chunks and externally generated embeddings."""

from collections.abc import Sequence
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.api.types import GetResult, QueryResult
from chromadb.errors import NotFoundError

from app.chunking import DocumentChunk


class VectorStoreError(RuntimeError):
    """Raised when Chroma initialization or persistence fails."""


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """One nearest-neighbor result returned from the cosine collection."""

    chunk_id: str
    text: str
    metadata: dict[str, str | int | float | bool]
    distance: float
    similarity: float


def cosine_distance_to_similarity(distance: float) -> float:
    """Convert verified Chroma cosine distance to cosine similarity."""

    if not math.isfinite(distance):
        raise ValueError("Cosine distance must be a finite number.")
    return 1.0 - distance


class ChromaVectorStore:
    """Store one active document in a persistent cosine-distance collection."""

    def __init__(self, *, path: str | Path, collection_name: str) -> None:
        self.path = Path(path)
        self.collection_name = collection_name

        try:
            self._client = chromadb.PersistentClient(path=str(self.path))
        except Exception as exc:
            raise VectorStoreError(
                f"Could not initialize Chroma at '{self.path}'."
            ) from exc

    def replace_chunks(
        self,
        chunks: Sequence[DocumentChunk],
        embeddings: Sequence[Sequence[float]],
        *,
        embedding_model: str,
    ) -> None:
        """Replace the active collection after embeddings are ready."""

        if not chunks:
            raise ValueError("At least one chunk is required for indexing.")
        if len(chunks) != len(embeddings):
            raise ValueError("Each chunk must have exactly one embedding.")
        if any(not embedding for embedding in embeddings):
            raise ValueError("Embedding vectors cannot be empty.")

        source = chunks[0].source
        if any(chunk.source != source for chunk in chunks):
            raise ValueError("One Chroma collection can contain only one source document.")

        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [_chunk_metadata(chunk) for chunk in chunks]
        embedding_values = [list(embedding) for embedding in embeddings]

        try:
            self._delete_collection_if_present()
            collection = self._client.create_collection(
                name=self.collection_name,
                configuration={"hnsw": {"space": "cosine"}},
                metadata={
                    "embedding_model": embedding_model,
                    "source": source,
                },
                embedding_function=None,
            )
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embedding_values,
            )
        except Exception as exc:
            raise VectorStoreError(
                f"Failed to replace Chroma collection '{self.collection_name}'."
            ) from exc

    def count(self) -> int:
        """Return the number of records in the active collection."""

        return self._get_collection().count()

    def get_all(self) -> GetResult:
        """Fetch persisted records for inspection and tests."""

        return self._get_collection().get(
            include=["documents", "metadatas", "embeddings"]
        )

    def get_collection_configuration(self) -> dict[str, Any]:
        """Expose Chroma's public collection configuration for verification."""

        return self._get_collection().configuration

    def get_collection_metadata(self) -> dict[str, Any]:
        """Return minimal collection-level consistency metadata."""

        return dict(self._get_collection().metadata or {})

    def validate_embedding_model(self, expected_model: str) -> None:
        """Ensure query embeddings use the model that built the index."""

        configured_model = expected_model.strip()
        if not configured_model:
            raise ValueError("Expected embedding model cannot be empty.")

        indexed_model = self.get_collection_metadata().get("embedding_model")
        if not isinstance(indexed_model, str) or not indexed_model.strip():
            raise VectorStoreError(
                f"Chroma collection '{self.collection_name}' does not record "
                "its embedding model. Re-ingest the document."
            )
        if indexed_model != configured_model:
            raise VectorStoreError(
                "Embedding model mismatch: the index uses "
                f"'{indexed_model}', but queries use '{configured_model}'. "
                "Re-ingest the document with the configured embedding model."
            )

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        limit: int,
    ) -> list[RetrievedChunk]:
        """Return nearest chunks with raw cosine distance and similarity."""

        if not query_embedding:
            raise ValueError("Query embedding cannot be empty.")
        if limit <= 0:
            raise ValueError("Retrieval limit must be greater than zero.")

        collection = self._get_collection()
        try:
            record_count = collection.count()
            if record_count == 0:
                raise VectorStoreError(
                    f"Chroma collection '{self.collection_name}' is empty. "
                    "Ingest a document before retrieval."
                )

            result = collection.query(
                query_embeddings=[list(query_embedding)],
                n_results=min(limit, record_count),
                include=["documents", "metadatas", "distances"],
            )
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(
                f"Failed to search Chroma collection '{self.collection_name}'."
            ) from exc

        return _parse_single_query_result(result)

    def _get_collection(self) -> Collection:
        try:
            return self._client.get_collection(
                name=self.collection_name,
                embedding_function=None,
            )
        except NotFoundError as exc:
            raise VectorStoreError(
                f"Chroma collection '{self.collection_name}' does not exist."
            ) from exc
        except Exception as exc:
            raise VectorStoreError(
                f"Could not open Chroma collection '{self.collection_name}'."
            ) from exc

    def _delete_collection_if_present(self) -> None:
        try:
            self._client.delete_collection(self.collection_name)
        except NotFoundError:
            return


def _chunk_metadata(chunk: DocumentChunk) -> dict[str, str | int]:
    metadata: dict[str, str | int] = {
        "source": chunk.source,
        "token_count": chunk.token_count,
    }
    if chunk.section is not None:
        metadata["section"] = chunk.section
    return metadata


def _parse_single_query_result(result: QueryResult) -> list[RetrievedChunk]:
    ids = result.get("ids")
    documents = result.get("documents")
    metadatas = result.get("metadatas")
    distances = result.get("distances")

    nested_fields = (ids, documents, metadatas, distances)
    if any(field is None or len(field) != 1 for field in nested_fields):
        raise VectorStoreError("Chroma returned an invalid query result shape.")

    result_ids = ids[0]
    result_documents = documents[0]
    result_metadatas = metadatas[0]
    result_distances = distances[0]

    expected_length = len(result_ids)
    if any(
        len(field) != expected_length
        for field in (result_documents, result_metadatas, result_distances)
    ):
        raise VectorStoreError("Chroma returned incomplete query result fields.")

    retrieved: list[RetrievedChunk] = []
    for chunk_id, document, metadata, distance in zip(
        result_ids,
        result_documents,
        result_metadatas,
        result_distances,
        strict=True,
    ):
        if document is None or distance is None:
            raise VectorStoreError("Chroma returned an incomplete retrieval record.")

        raw_distance = float(distance)
        retrieved.append(
            RetrievedChunk(
                chunk_id=chunk_id,
                text=document,
                metadata=dict(metadata or {}),
                distance=raw_distance,
                similarity=cosine_distance_to_similarity(raw_distance),
            )
        )

    return retrieved
