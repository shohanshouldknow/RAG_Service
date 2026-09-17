"""Lazy construction of query-time application services."""

from functools import lru_cache

from pydantic import ValidationError

from app.config import ConfigurationError, Settings
from app.document_uploads import DocumentUploadService
from app.embeddings import EmbeddingService
from app.llm import LLMService
from app.rag import RAGService
from app.retrieval import RetrievalService
from app.vector_store import ChromaVectorStore


def _load_settings() -> Settings:
    """Load settings and translate validation details into a domain error."""

    try:
        return Settings()
    except ValidationError as exc:
        raise ConfigurationError("Application configuration is invalid.") from exc


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Load the local embedding model once for ingestion and retrieval."""

    settings = _load_settings()
    return EmbeddingService(model=settings.embedding_model)


@lru_cache(maxsize=1)
def get_vector_store() -> ChromaVectorStore:
    """Share one Chroma client for the configured active collection."""

    settings = _load_settings()
    return ChromaVectorStore(
        path=settings.chroma_path,
        collection_name=settings.chroma_collection,
    )


@lru_cache(maxsize=1)
def get_document_upload_service() -> DocumentUploadService:
    """Build the upload coordinator without initializing Ollama."""

    return DocumentUploadService(
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store(),
    )


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    """Build the query pipeline once, when the query endpoint first needs it."""

    settings = _load_settings()

    llm_model = settings.require_llm_model()
    min_similarity = settings.require_min_similarity()

    embedding_service = get_embedding_service()
    vector_store = get_vector_store()
    retrieval_service = RetrievalService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        top_k=settings.top_k,
        min_similarity=min_similarity,
    )
    llm_service = LLMService(
        model=llm_model,
        base_url=settings.ollama_base_url,
    )
    return RAGService(
        retrieval_service=retrieval_service,
        llm_service=llm_service,
    )
