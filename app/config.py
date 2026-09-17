"""Environment-based application configuration."""

from pathlib import Path
from typing import Final

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


APP_TITLE: Final[str] = "DocuSense"


class ConfigurationError(ValueError):
    """Raised when required runtime configuration is missing."""


class Settings(BaseSettings):
    """Settings required by the current application phases."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_model: str = "qwen2.5:3b"
    ollama_base_url: str = "http://localhost:11434"
    chroma_path: Path = Path("storage/chroma")
    chroma_collection: str = "docusense"
    top_k: int = Field(default=4, ge=1)
    min_similarity: float | None = Field(default=None, ge=-1.0, le=1.0)

    def require_llm_model(self) -> str:
        """Return a non-empty local generation model name."""

        if not self.llm_model.strip():
            raise ConfigurationError(
                "LLM_MODEL is required for grounded answer generation."
            )
        return self.llm_model.strip()

    def require_min_similarity(self) -> float:
        """Return the threshold only after it has been explicitly calibrated."""

        if self.min_similarity is None:
            raise ConfigurationError(
                "MIN_SIMILARITY must be configured after calibration against "
                "the indexed document."
            )
        return self.min_similarity
