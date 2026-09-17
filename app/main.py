"""FastAPI application, HTTP routes, and static frontend serving."""

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import APP_TITLE, ConfigurationError
from app.dependencies import get_document_upload_service, get_rag_service
from app.document_loader import DocumentLoadError
from app.document_uploads import (
    DocumentUploadProcessingError,
    DocumentUploadService,
    DocumentUploadTooLargeError,
    DocumentUploadValidationError,
    UnsupportedDocumentTypeError,
)
from app.embeddings import EmbeddingError
from app.llm import LLMError
from app.rag import RAGService
from app.schemas import (
    DocumentUploadResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    SourceResponse,
)
from app.vector_store import VectorStoreError


app = FastAPI(title=APP_TITLE)
STATIC_DIRECTORY = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")


@app.get("/", include_in_schema=False)
def web_interface() -> FileResponse:
    """Serve the optional document upload and query interface."""

    return FileResponse(STATIC_DIRECTORY / "index.html")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report that the API process is running."""

    return HealthResponse(status="ok")


@app.post(
    "/api/documents",
    response_model=DocumentUploadResponse,
    status_code=201,
)
def upload_document(
    file: Annotated[UploadFile, File(...)],
    upload_service: Annotated[
        DocumentUploadService,
        Depends(get_document_upload_service),
    ],
) -> DocumentUploadResponse:
    """Replace the active corpus using one validated document upload."""

    result = upload_service.ingest(filename=file.filename, stream=file.file)
    return DocumentUploadResponse(
        filename=result.source,
        chunks_indexed=result.chunks_indexed,
        status="ready",
    )


@app.post("/api/query", response_model=QueryResponse)
def query_document(
    request: QueryRequest,
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
) -> QueryResponse:
    """Return a grounded answer from the configured document index."""

    result = rag_service.answer(request.question)
    return QueryResponse(
        answer=result.answer,
        sources=[
            SourceResponse(
                chunk_id=source.chunk_id,
                similarity_score=source.similarity,
                text_snippet=source.text,
            )
            for source in result.sources
        ],
        tokens_used=result.tokens_used,
    )


@app.exception_handler(ConfigurationError)
def handle_configuration_error(
    _request: Request,
    exception: ConfigurationError,
) -> JSONResponse:
    """Report safe, actionable missing query configuration."""

    return JSONResponse(
        status_code=503,
        content={"detail": str(exception)},
    )


@app.exception_handler(UnsupportedDocumentTypeError)
def handle_unsupported_document_type(
    _request: Request,
    exception: UnsupportedDocumentTypeError,
) -> JSONResponse:
    """Reject unsupported uploads without attempting ingestion."""

    return JSONResponse(status_code=415, content={"detail": str(exception)})


@app.exception_handler(DocumentUploadTooLargeError)
def handle_document_too_large(
    _request: Request,
    exception: DocumentUploadTooLargeError,
) -> JSONResponse:
    """Report the fixed upload size limit."""

    return JSONResponse(status_code=413, content={"detail": str(exception)})


@app.exception_handler(DocumentUploadValidationError)
def handle_invalid_document_upload(
    _request: Request,
    exception: DocumentUploadValidationError,
) -> JSONResponse:
    """Return a clear client error for an unusable upload."""

    return JSONResponse(status_code=400, content={"detail": str(exception)})


@app.exception_handler(DocumentLoadError)
def handle_uploaded_document_load_error(
    _request: Request,
    _exception: DocumentLoadError,
) -> JSONResponse:
    """Hide temporary paths while describing invalid document content."""

    return JSONResponse(
        status_code=400,
        content={
            "detail": "The uploaded document must contain non-empty UTF-8 text."
        },
    )


@app.exception_handler(DocumentUploadProcessingError)
def handle_document_upload_processing_error(
    _request: Request,
    _exception: DocumentUploadProcessingError,
) -> JSONResponse:
    """Hide staging details while reporting a technical upload failure."""

    return JSONResponse(
        status_code=500,
        content={"detail": "The uploaded document could not be processed."},
    )


@app.exception_handler(VectorStoreError)
def handle_vector_store_error(
    _request: Request,
    _exception: VectorStoreError,
) -> JSONResponse:
    """Hide storage paths while reporting an unavailable document index."""

    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "Document index is unavailable or incompatible. "
                "Ingest the document using the current configuration."
            )
        },
    )


@app.exception_handler(EmbeddingError)
@app.exception_handler(LLMError)
def handle_provider_error(
    _request: Request,
    _exception: EmbeddingError | LLMError,
) -> JSONResponse:
    """Return a concise upstream error without exposing provider details."""

    return JSONResponse(
        status_code=502,
        content={"detail": "AI provider request failed."},
    )


@app.exception_handler(Exception)
def handle_unexpected_error(
    _request: Request,
    _exception: Exception,
) -> JSONResponse:
    """Prevent unexpected internal details from reaching API clients."""

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )
