"""Question embedding and retrieval-confidence filtering."""

from app.embeddings import EmbeddingService
from app.vector_store import ChromaVectorStore, RetrievedChunk


class RetrievalError(RuntimeError):
    """Raised when retrieval cannot produce a valid question embedding."""


class RetrievalService:
    """Retrieve only chunks that meet the configured evidence threshold."""

    def __init__(
        self,
        *,
        embedding_service: EmbeddingService,
        vector_store: ChromaVectorStore,
        top_k: int,
        min_similarity: float,
    ) -> None:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")
        if not -1.0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity must be between -1 and 1.")

        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._top_k = top_k
        self._min_similarity = min_similarity

    def retrieve(self, question: str) -> list[RetrievedChunk]:
        """Embed a question and return only sufficiently similar chunks."""

        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("Question cannot be empty.")

        self._vector_store.validate_embedding_model(self._embedding_service.model)
        embeddings = self._embedding_service.embed_texts([normalized_question])
        if len(embeddings) != 1 or not embeddings[0]:
            raise RetrievalError(
                "Embedding service did not return one valid question embedding."
            )

        candidates = self._vector_store.search(
            embeddings[0],
            limit=self._top_k,
        )
        return [
            candidate
            for candidate in candidates
            if candidate.similarity >= self._min_similarity
        ]
