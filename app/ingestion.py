"""Coordination for offline document indexing."""

from dataclasses import dataclass
from pathlib import Path

from app.chunking import chunk_document
from app.document_loader import load_document
from app.embeddings import EmbeddingService, build_embedding_text
from app.vector_store import ChromaVectorStore


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """Small summary returned after successful indexing."""

    source: str
    chunks_indexed: int
    collection_name: str


def ingest_document(
    document_path: str | Path,
    *,
    embedding_service: EmbeddingService,
    vector_store: ChromaVectorStore,
) -> IngestionResult:
    """Load, chunk, embed, and persist one document."""

    document = load_document(document_path)
    chunks = chunk_document(document)
    embedding_inputs = [build_embedding_text(chunk) for chunk in chunks]

    # The collection is intentionally untouched until every embedding succeeds.
    embeddings = embedding_service.embed_texts(embedding_inputs)
    vector_store.replace_chunks(
        chunks,
        embeddings,
        embedding_model=embedding_service.model,
    )

    return IngestionResult(
        source=document.source,
        chunks_indexed=len(chunks),
        collection_name=vector_store.collection_name,
    )
