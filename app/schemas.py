"""Public API request and response schemas."""

from typing import Final, Literal

from pydantic import BaseModel, Field, field_validator


MAX_QUESTION_LENGTH: Final[int] = 2_000


class HealthResponse(BaseModel):
    """Response returned by the health endpoint."""

    status: Literal["ok"]


class DocumentUploadResponse(BaseModel):
    """Summary returned after replacing the active document index."""

    filename: str
    chunks_indexed: int = Field(ge=1)
    status: Literal["ready"]


class QueryRequest(BaseModel):
    """Validated question submitted to the grounded query endpoint."""

    question: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)

    @field_validator("question", mode="before")
    @classmethod
    def strip_question(cls, value: object) -> object:
        """Normalize surrounding whitespace before length validation."""

        if isinstance(value, str):
            return value.strip()
        return value


class SourceResponse(BaseModel):
    """One evidence chunk supplied to grounded generation."""

    chunk_id: str
    similarity_score: float
    text_snippet: str


class QueryResponse(BaseModel):
    """Grounded answer and the evidence used to produce it."""

    answer: str
    sources: list[SourceResponse]
    tokens_used: int = Field(ge=0)
