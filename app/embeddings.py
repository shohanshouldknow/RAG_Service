"""Local sentence-transformer embeddings for document chunks and queries."""

from typing import Any

from app.chunking import DocumentChunk


class EmbeddingError(RuntimeError):
    """Raised when embedding generation fails or returns invalid data."""


def build_embedding_text(chunk: DocumentChunk) -> str:
    """Add section context without changing the stored source text."""

    if chunk.section is None:
        return chunk.text
    return f"{chunk.section}\n\n{chunk.text}"


class EmbeddingService:
    """Small synchronous wrapper around a local SentenceTransformer model."""

    def __init__(
        self,
        *,
        model: str,
        encoder: Any | None = None,
        batch_size: int = 32,
    ) -> None:
        model_name = model.strip()
        if not model_name:
            raise ValueError("Embedding model name cannot be empty.")
        if batch_size <= 0:
            raise ValueError("Embedding batch size must be greater than zero.")

        if encoder is None:
            try:
                from sentence_transformers import SentenceTransformer

                encoder = SentenceTransformer(model_name)
            except Exception as exc:
                raise EmbeddingError(
                    f"Could not load local embedding model '{model_name}'."
                ) from exc

        self.model = model_name
        self._encoder = encoder
        self._batch_size = batch_size

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed texts locally in batches and return plain float vectors."""

        if not texts:
            return []

        try:
            encoded = self._encoder.encode(
                texts,
                batch_size=self._batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        except Exception as exc:
            raise EmbeddingError("Local embedding generation failed.") from exc

        try:
            embeddings = [
                [float(value) for value in vector]
                for vector in encoded
            ]
        except (TypeError, ValueError) as exc:
            raise EmbeddingError(
                "Local embedding model returned invalid vectors."
            ) from exc

        if len(embeddings) != len(texts) or any(not vector for vector in embeddings):
            raise EmbeddingError(
                "Local embedding model returned an unexpected number of vectors."
            )
        return embeddings
