"""Grounded retrieval-and-generation coordination."""

from dataclasses import dataclass

from app.constants import INSUFFICIENT_DOCUMENTATION_MESSAGE
from app.llm import LLMService
from app.prompts import GROUNDING_INSTRUCTIONS, build_grounded_input
from app.retrieval import RetrievalService
from app.vector_store import RetrievedChunk


@dataclass(frozen=True, slots=True)
class RAGResult:
    """Grounded answer data for the future API layer."""

    answer: str
    sources: list[RetrievedChunk]
    tokens_used: int


class RAGService:
    """Coordinate retrieval guardrails and grounded generation."""

    def __init__(
        self,
        *,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._llm_service = llm_service

    def answer(self, question: str) -> RAGResult:
        """Answer from qualifying evidence or return the exact fallback."""

        qualifying_chunks = self._retrieval_service.retrieve(question)
        if not qualifying_chunks:
            return RAGResult(
                answer=INSUFFICIENT_DOCUMENTATION_MESSAGE,
                sources=[],
                tokens_used=0,
            )

        grounded_input = build_grounded_input(question, qualifying_chunks)
        generation = self._llm_service.generate(
            instructions=GROUNDING_INSTRUCTIONS,
            input_text=grounded_input,
        )

        if INSUFFICIENT_DOCUMENTATION_MESSAGE in generation.answer:
            return RAGResult(
                answer=INSUFFICIENT_DOCUMENTATION_MESSAGE,
                sources=[],
                tokens_used=generation.tokens_used,
            )

        return RAGResult(
            answer=generation.answer,
            sources=list(qualifying_chunks),
            tokens_used=generation.tokens_used,
        )
