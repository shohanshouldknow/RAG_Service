"""Safe loading for the document types supported by DocuSense."""

from dataclasses import dataclass
from pathlib import Path
from typing import Final


SUPPORTED_DOCUMENT_EXTENSIONS: Final[frozenset[str]] = frozenset({".md", ".txt"})


class DocumentLoadError(ValueError):
    """Raised when a document cannot be loaded safely."""


@dataclass(frozen=True, slots=True)
class LoadedDocument:
    """Text and basic metadata read from a supported document."""

    text: str
    source: str
    extension: str


def load_document(path: str | Path) -> LoadedDocument:
    """Load and validate one UTF-8 Markdown or plain-text document."""

    document_path = Path(path)

    if not document_path.exists():
        raise DocumentLoadError(f"Document does not exist: {document_path}")
    if not document_path.is_file():
        raise DocumentLoadError(f"Document path is not a file: {document_path}")

    extension = document_path.suffix.lower()
    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        raise DocumentLoadError(
            f"Unsupported document type '{extension or '[no extension]'}'. "
            "Only .md and .txt files are supported."
        )

    try:
        raw_text = document_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentLoadError(
            f"Document must be UTF-8 encoded: {document_path}"
        ) from exc
    except OSError as exc:
        raise DocumentLoadError(f"Could not read document: {document_path}") from exc

    text = _normalize_text(raw_text)
    if not text:
        raise DocumentLoadError(f"Document is empty: {document_path}")

    return LoadedDocument(
        text=text,
        source=document_path.name,
        extension=extension,
    )


def _normalize_text(text: str) -> str:
    """Normalize line endings while preserving document wording."""

    return text.replace("\r\n", "\n").replace("\r", "\n").strip()
