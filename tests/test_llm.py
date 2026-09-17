"""Tests for the local Ollama generation wrapper."""

from types import SimpleNamespace

import pytest

from app.config import Settings
from app.llm import LLMError, LLMService


class FakeOllamaClient:
    def __init__(self, response: SimpleNamespace) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []
        self.error: Exception | None = None

    def generate(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


def _response(
    answer: str,
    prompt_tokens: int | None = 11,
    output_tokens: int | None = 6,
) -> SimpleNamespace:
    return SimpleNamespace(
        response=answer,
        prompt_eval_count=prompt_tokens,
        eval_count=output_tokens,
    )


def test_generate_uses_ollama_and_sums_reported_token_counts() -> None:
    client = FakeOllamaClient(_response("Supported answer.", 17, 6))
    service = LLMService(
        model="configured-llm-model",
        base_url="http://localhost:11434",
        client=client,
    )

    result = service.generate(
        instructions="Synthetic system instructions.",
        input_text="Synthetic context and question.",
    )

    assert result.answer == "Supported answer."
    assert result.tokens_used == 23
    assert client.calls == [
        {
            "model": "configured-llm-model",
            "system": "Synthetic system instructions.",
            "prompt": "Synthetic context and question.",
            "stream": False,
            "options": {"temperature": 0.0},
        }
    ]


@pytest.mark.parametrize(
    ("prompt_tokens", "output_tokens"),
    [(None, None), (10, None), (None, 5)],
)
def test_incomplete_usage_returns_zero_without_estimating(
    prompt_tokens: int | None,
    output_tokens: int | None,
) -> None:
    service = LLMService(
        model="synthetic-model",
        base_url="http://localhost:11434",
        client=FakeOllamaClient(
            _response("Answer.", prompt_tokens, output_tokens)
        ),
    )

    assert service.generate(instructions="Rules.", input_text="Input.").tokens_used == 0


def test_provider_failure_is_a_technical_error() -> None:
    client = FakeOllamaClient(_response("Unused answer."))
    client.error = RuntimeError("synthetic provider failure")
    service = LLMService(
        model="synthetic-model",
        base_url="http://localhost:11434",
        client=client,
    )

    with pytest.raises(LLMError, match="generation failed") as exc_info:
        service.generate(instructions="Rules.", input_text="Input.")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_empty_output_is_an_invalid_response_error() -> None:
    service = LLMService(
        model="synthetic-model",
        base_url="http://localhost:11434",
        client=FakeOllamaClient(_response("   ")),
    )

    with pytest.raises(LLMError, match="valid output text"):
        service.generate(instructions="Rules.", input_text="Input.")


def test_invalid_token_usage_is_rejected() -> None:
    service = LLMService(
        model="synthetic-model",
        base_url="http://localhost:11434",
        client=FakeOllamaClient(_response("Answer.", -1, 5)),
    )

    with pytest.raises(LLMError, match="invalid token usage"):
        service.generate(instructions="Rules.", input_text="Input.")


def test_local_llm_defaults_can_be_overridden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    defaults = Settings(_env_file=None)
    assert defaults.require_llm_model() == "qwen2.5:3b"
    assert defaults.ollama_base_url == "http://localhost:11434"

    monkeypatch.setenv("LLM_MODEL", "synthetic-generation-model")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:21434")
    configured = Settings(_env_file=None)
    assert configured.require_llm_model() == "synthetic-generation-model"
    assert configured.ollama_base_url == "http://localhost:21434"
