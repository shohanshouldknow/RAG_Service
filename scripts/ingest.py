"""Command-line entry point for offline document ingestion."""

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from app.config import Settings
from app.embeddings import EmbeddingError, EmbeddingService
from app.ingestion import ingest_document
from app.vector_store import ChromaVectorStore, VectorStoreError


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index one Markdown or plain-text document into Chroma."
    )
    parser.add_argument("document", type=Path, help="Path to a .md or .txt document")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        settings = Settings()
        embedding_service = EmbeddingService(
            model=settings.embedding_model,
        )
        vector_store = ChromaVectorStore(
            path=settings.chroma_path,
            collection_name=settings.chroma_collection,
        )
        result = ingest_document(
            args.document,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
    except (ValueError, EmbeddingError, VectorStoreError) as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Indexed {result.source}: {result.chunks_indexed} chunks "
        f"into collection '{result.collection_name}'."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
