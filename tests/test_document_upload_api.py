"""Tests for the optional document upload API and static interface."""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.document_uploads as document_uploads
from app.dependencies import get_document_upload_service
from app.document_uploads import DocumentUploadService, MAX_UPLOAD_BYTES
from app.embeddings import EmbeddingError
from app.ingestion import IngestionResult
from app.main import app


class FakeIngestion:
    """Capture the temporary document passed to the existing pipeline."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.paths: list[Path] = []
        self.contents: list[bytes] = []
        self.embedding_services: list[Any] = []
        self.vector_stores: list[Any] = []

    def __call__(
        self,
        document_path: str | Path,
        *,
        embedding_service: Any,
        vector_store: Any,
    ) -> IngestionResult:
        path = Path(document_path)
        assert path.exists()
        self.paths.append(path)
        self.contents.append(path.read_bytes())
        self.embedding_services.append(embedding_service)
        self.vector_stores.append(vector_store)
        if self.error is not None:
            raise self.error
        return IngestionResult(
            source=path.name,
            chunks_indexed=3,
            collection_name="synthetic-collection",
        )


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides.clear()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _use_fake_ingestion(
    monkeypatch: pytest.MonkeyPatch,
    fake_ingestion: FakeIngestion,
) -> tuple[object, object]:
    embedding_service = object()
    vector_store = object()
    upload_service = DocumentUploadService(
        embedding_service=embedding_service,  # type: ignore[arg-type]
        vector_store=vector_store,  # type: ignore[arg-type]
    )
    app.dependency_overrides[get_document_upload_service] = lambda: upload_service
    monkeypatch.setattr(document_uploads, "ingest_document", fake_ingestion)
    return embedding_service, vector_store


def test_root_serves_frontend(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "DocuSense" in response.text
    assert "Grounded Document Q&amp;A" in response.text
    assert "Kamruzzaman Shohan" in response.text
    assert 'href="https://kshohan.vercel.app"' in response.text


def test_markdown_upload_uses_ingestion_and_cleans_temporary_file(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    fake_ingestion = FakeIngestion()
    embedding_service, vector_store = _use_fake_ingestion(monkeypatch, fake_ingestion)

    response = client.post(
        "/api/documents",
        files={
            "file": (
                "../../policies.md",
                b"# Synthetic policy\n\nRetain records for 30 days.",
                "text/markdown",
            )
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "filename": "policies.md",
        "chunks_indexed": 3,
        "status": "ready",
    }
    assert fake_ingestion.contents == [
        b"# Synthetic policy\n\nRetain records for 30 days."
    ]
    assert fake_ingestion.embedding_services == [embedding_service]
    assert fake_ingestion.vector_stores == [vector_store]
    assert len(fake_ingestion.paths) == 1
    assert not fake_ingestion.paths[0].exists()


def test_plain_text_upload_works(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    fake_ingestion = FakeIngestion()
    _use_fake_ingestion(monkeypatch, fake_ingestion)

    response = client.post(
        "/api/documents",
        files={"file": ("notes.txt", b"Synthetic plain text.", "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["filename"] == "notes.txt"
    assert fake_ingestion.paths[0].suffix == ".txt"
    assert not fake_ingestion.paths[0].exists()


def test_unsupported_extension_is_rejected_before_ingestion(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    fake_ingestion = FakeIngestion()
    _use_fake_ingestion(monkeypatch, fake_ingestion)

    response = client.post(
        "/api/documents",
        files={"file": ("policies.pdf", b"not a PDF", "application/pdf")},
    )

    assert response.status_code == 415
    assert response.json() == {
        "detail": "Only .md and .txt document uploads are supported."
    }
    assert fake_ingestion.paths == []


def test_empty_upload_is_rejected_before_ingestion(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    fake_ingestion = FakeIngestion()
    _use_fake_ingestion(monkeypatch, fake_ingestion)

    response = client.post(
        "/api/documents",
        files={"file": ("empty.md", b"", "text/markdown")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "The uploaded document is empty."}
    assert fake_ingestion.paths == []


def test_oversized_upload_is_rejected_before_ingestion(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    fake_ingestion = FakeIngestion()
    _use_fake_ingestion(monkeypatch, fake_ingestion)

    response = client.post(
        "/api/documents",
        files={
            "file": (
                "large.txt",
                b"x" * (MAX_UPLOAD_BYTES + 1),
                "text/plain",
            )
        },
    )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "The uploaded document exceeds the 5 MB size limit."
    }
    assert fake_ingestion.paths == []


def test_ingestion_failure_is_technical_error_and_cleans_temporary_file(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    fake_ingestion = FakeIngestion(
        error=EmbeddingError("sensitive local model detail")
    )
    _use_fake_ingestion(monkeypatch, fake_ingestion)

    response = client.post(
        "/api/documents",
        files={"file": ("policies.md", b"# Valid content", "text/markdown")},
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "AI provider request failed."}
    assert "sensitive" not in response.text
    assert len(fake_ingestion.paths) == 1
    assert not fake_ingestion.paths[0].exists()
