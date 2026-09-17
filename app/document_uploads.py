"""Validation and temporary staging for uploaded documents."""

from dataclasses import dataclass
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from typing import BinaryIO, Final

from app.document_loader import SUPPORTED_DOCUMENT_EXTENSIONS
from app.embeddings import EmbeddingService
from app.ingestion import IngestionResult, ingest_document
from app.vector_store import ChromaVectorStore


MAX_UPLOAD_BYTES: Final[int] = 5 * 1024 * 1024
_MAX_FILENAME_STEM_LENGTH: Final[int] = 180
_UNSAFE_FILENAME_CHARACTERS = re.compile(r"[^A-Za-z0-9._ -]+")


class DocumentUploadValidationError(ValueError):
    """Raised when an uploaded file is not safe or usable."""


class UnsupportedDocumentTypeError(DocumentUploadValidationError):
    """Raised when an upload is not Markdown or plain text."""


class EmptyDocumentUploadError(DocumentUploadValidationError):
    """Raised when an uploaded file has no bytes."""


class DocumentUploadTooLargeError(DocumentUploadValidationError):
    """Raised when an upload exceeds the configured byte limit."""


class DocumentUploadProcessingError(RuntimeError):
    """Raised when an upload cannot be safely staged for ingestion."""


@dataclass(frozen=True, slots=True)
class DocumentUploadService:
    """Stage one safe upload and pass it to the existing ingestion pipeline."""

    embedding_service: EmbeddingService
    vector_store: ChromaVectorStore

    def ingest(self, *, filename: str | None, stream: BinaryIO) -> IngestionResult:
        """Validate, temporarily stage, ingest, and clean up one upload."""

        safe_filename = _sanitize_filename(filename)
        content = _read_limited(stream)

        try:
            with TemporaryDirectory(prefix="docusense_upload_") as directory:
                temporary_path = Path(directory) / safe_filename
                temporary_path.write_bytes(content)
                return ingest_document(
                    temporary_path,
                    embedding_service=self.embedding_service,
                    vector_store=self.vector_store,
                )
        except OSError as exc:
            raise DocumentUploadProcessingError(
                "The uploaded document could not be staged for ingestion."
            ) from exc


def _sanitize_filename(filename: str | None) -> str:
    """Return a safe basename while preserving a supported extension."""

    if not filename or "\x00" in filename:
        raise DocumentUploadValidationError("A valid filename is required.")

    basename = filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1].strip()
    sanitized = _UNSAFE_FILENAME_CHARACTERS.sub("_", basename).strip(" .")
    extension = Path(sanitized).suffix.lower()
    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        raise UnsupportedDocumentTypeError(
            "Only .md and .txt document uploads are supported."
        )

    stem = Path(sanitized).stem.strip(" ._")
    if not stem:
        raise DocumentUploadValidationError("A valid filename is required.")

    return f"{stem[:_MAX_FILENAME_STEM_LENGTH]}{extension}"


def _read_limited(stream: BinaryIO) -> bytes:
    """Read no more than one byte beyond the upload limit."""

    try:
        content = stream.read(MAX_UPLOAD_BYTES + 1)
    except OSError as exc:
        raise DocumentUploadProcessingError(
            "The uploaded document could not be read."
        ) from exc

    if not isinstance(content, bytes):
        raise DocumentUploadProcessingError(
            "The uploaded document did not contain binary file data."
        )
    if len(content) > MAX_UPLOAD_BYTES:
        raise DocumentUploadTooLargeError(
            "The uploaded document exceeds the 5 MB size limit."
        )
    if not content:
        raise EmptyDocumentUploadError("The uploaded document is empty.")
    return content
