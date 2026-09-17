"""Small Ollama wrapper for local grounded generation."""

from dataclasses import dataclass
from typing import Any


class LLMError(RuntimeError):
    """Raised when answer generation fails or returns invalid data."""


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Generated text and provider-reported token usage."""

    answer: str
    tokens_used: int


class LLMService:
    """Synchronous, injectable wrapper around a local Ollama service."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        client: Any | None = None,
    ) -> None:
        model_name = model.strip()
        if not model_name:
            raise ValueError("LLM model name cannot be empty.")
        service_url = base_url.strip()
        if not service_url:
            raise ValueError("Ollama base URL cannot be empty.")

        if client is None:
            try:
                from ollama import Client

                client = Client(host=service_url)
            except Exception as exc:
                raise LLMError("Could not initialize the local Ollama client.") from exc

        self.model = model_name
        self.base_url = service_url
        self._client = client

    def generate(self, *, instructions: str, input_text: str) -> GenerationResult:
        """Generate one non-streaming grounded answer through local Ollama."""

        if not instructions.strip():
            raise ValueError("LLM instructions cannot be empty.")
        if not input_text.strip():
            raise ValueError("LLM input cannot be empty.")

        try:
            response = self._client.generate(
                model=self.model,
                system=instructions,
                prompt=input_text,
                stream=False,
                options={"temperature": 0.0},
            )
        except Exception as exc:
            raise LLMError("Ollama generation failed.") from exc

        answer = getattr(response, "response", None)
        if not isinstance(answer, str) or not answer.strip():
            raise LLMError("Ollama response did not contain valid output text.")

        return GenerationResult(
            answer=answer.strip(),
            tokens_used=_extract_total_tokens(response),
        )


def _extract_total_tokens(response: object) -> int:
    prompt_tokens = getattr(response, "prompt_eval_count", None)
    output_tokens = getattr(response, "eval_count", None)
    if prompt_tokens is None or output_tokens is None:
        return 0

    for count in (prompt_tokens, output_tokens):
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise LLMError("Ollama response contained invalid token usage.")
    return prompt_tokens + output_tokens
