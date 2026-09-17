"""Measure MiniLM retrieval scores against the synthetic demonstration corpus."""

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any

from app.config import Settings
from app.embeddings import EmbeddingError, EmbeddingService
from app.vector_store import ChromaVectorStore, VectorStoreError


EXPECTED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EXPECTED_RECORD_COUNT = 14
QUESTIONS_PATH = Path("evaluation/questions.json")
SUPPORTED_CATEGORIES = {"direct_supported", "paraphrased_supported"}
EXPECTED_CATEGORY_COUNTS = {
    "direct_supported": 8,
    "paraphrased_supported": 4,
    "unsupported": 8,
}


class EvaluationError(RuntimeError):
    """Raised when the evaluation inputs or index are not as expected."""


@dataclass(frozen=True, slots=True)
class QuestionCase:
    """One retrieval question and its expected category."""

    case_id: str
    category: str
    question: str
    expected_section: str | None


@dataclass(frozen=True, slots=True)
class ScoreRow:
    """Top retrieval measurement for one evaluation question."""

    case: QuestionCase
    chunk_id: str
    section: str | None
    distance: float
    similarity: float


def main() -> int:
    """Verify the index, measure all questions, and print score ranges."""

    try:
        cases = _load_cases(QUESTIONS_PATH)
        settings = Settings()
        vector_store = ChromaVectorStore(
            path=settings.chroma_path,
            collection_name=settings.chroma_collection,
        )
        _verify_index(vector_store, configured_model=settings.embedding_model)

        embedding_service = EmbeddingService(model=settings.embedding_model)
        embeddings = embedding_service.embed_texts(
            [case.question for case in cases]
        )
        rows = _measure(cases, embeddings, vector_store, top_k=settings.top_k)
    except (
        EvaluationError,
        EmbeddingError,
        OSError,
        ValueError,
        VectorStoreError,
        json.JSONDecodeError,
    ) as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        return 1

    _print_index_summary(settings, vector_store)
    _print_score_table(rows)
    _print_ranges(rows)
    _print_section_misses(rows)
    return 0


def _load_cases(path: Path) -> list[QuestionCase]:
    raw_data: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict):
        raise EvaluationError("Question data must be a JSON object.")

    raw_cases = raw_data.get("evaluation_questions")
    if not isinstance(raw_cases, list):
        raise EvaluationError("evaluation_questions must be a JSON array.")

    cases: list[QuestionCase] = []
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise EvaluationError("Each evaluation question must be an object.")

        case_id = raw_case.get("id")
        category = raw_case.get("category")
        question = raw_case.get("question")
        expected_section = raw_case.get("expected_section")
        if not all(isinstance(value, str) and value.strip() for value in (
            case_id,
            category,
            question,
        )):
            raise EvaluationError("Every question needs a non-empty id, category, and text.")
        if expected_section is not None and not isinstance(expected_section, str):
            raise EvaluationError("expected_section must be a string when provided.")

        cases.append(
            QuestionCase(
                case_id=case_id,
                category=category,
                question=question,
                expected_section=expected_section,
            )
        )

    actual_counts = {
        category: sum(case.category == category for case in cases)
        for category in EXPECTED_CATEGORY_COUNTS
    }
    if actual_counts != EXPECTED_CATEGORY_COUNTS:
        raise EvaluationError(
            f"Expected category counts {EXPECTED_CATEGORY_COUNTS}, got {actual_counts}."
        )
    if len({case.case_id for case in cases}) != len(cases):
        raise EvaluationError("Evaluation question IDs must be unique.")
    return cases


def _verify_index(
    vector_store: ChromaVectorStore,
    *,
    configured_model: str,
) -> None:
    if configured_model != EXPECTED_MODEL:
        raise EvaluationError(
            f"Expected configured model '{EXPECTED_MODEL}', got '{configured_model}'."
        )

    record_count = vector_store.count()
    if record_count != EXPECTED_RECORD_COUNT:
        raise EvaluationError(
            f"Expected {EXPECTED_RECORD_COUNT} indexed chunks, got {record_count}."
        )

    metadata = vector_store.get_collection_metadata()
    indexed_model = metadata.get("embedding_model")
    if indexed_model != EXPECTED_MODEL:
        raise EvaluationError(
            f"Expected index model '{EXPECTED_MODEL}', got '{indexed_model}'."
        )

    configuration = vector_store.get_collection_configuration()
    hnsw_configuration = configuration.get("hnsw")
    if not isinstance(hnsw_configuration, dict):
        raise EvaluationError("Chroma collection has no HNSW configuration.")
    if hnsw_configuration.get("space") != "cosine":
        raise EvaluationError("Chroma collection is not configured for cosine distance.")


def _measure(
    cases: list[QuestionCase],
    embeddings: list[list[float]],
    vector_store: ChromaVectorStore,
    *,
    top_k: int,
) -> list[ScoreRow]:
    if len(cases) != len(embeddings):
        raise EvaluationError("Each evaluation question must have one embedding.")

    rows: list[ScoreRow] = []
    for case, embedding in zip(cases, embeddings, strict=True):
        matches = vector_store.search(embedding, limit=top_k)
        if not matches:
            raise EvaluationError(f"No retrieval result was returned for {case.case_id}.")
        top_match = matches[0]
        section = top_match.metadata.get("section")
        rows.append(
            ScoreRow(
                case=case,
                chunk_id=top_match.chunk_id,
                section=section if isinstance(section, str) else None,
                distance=top_match.distance,
                similarity=top_match.similarity,
            )
        )
    return rows


def _print_index_summary(
    settings: Settings,
    vector_store: ChromaVectorStore,
) -> None:
    print("Index verification")
    print(f"  collection: {settings.chroma_collection}")
    print(f"  records: {vector_store.count()}")
    print(f"  embedding model: {settings.embedding_model}")
    print("  distance metric: cosine")
    print(f"  TOP_K: {settings.top_k}")


def _print_score_table(rows: list[ScoreRow]) -> None:
    print("\nRetrieval scores")
    print("ID  | Category              | Top chunk | Raw distance | Similarity | Question")
    print("----|-----------------------|-----------|--------------|------------|---------")
    for row in rows:
        print(
            f"{row.case.case_id:<3} | {row.case.category:<21} | "
            f"{row.chunk_id:<9} | {row.distance:>12.6f} | "
            f"{row.similarity:>10.6f} | {row.case.question}"
        )


def _print_ranges(rows: list[ScoreRow]) -> None:
    supported_scores = [
        row.similarity
        for row in rows
        if row.case.category in SUPPORTED_CATEGORIES
    ]
    unsupported_scores = [
        row.similarity for row in rows if row.case.category == "unsupported"
    ]
    print("\nScore ranges")
    print(
        "  supported:   "
        f"{min(supported_scores):.6f} to {max(supported_scores):.6f}"
    )
    print(
        "  unsupported: "
        f"{min(unsupported_scores):.6f} to {max(unsupported_scores):.6f}"
    )


def _print_section_misses(rows: list[ScoreRow]) -> None:
    misses = [
        row
        for row in rows
        if row.case.expected_section is not None
        and row.section != row.case.expected_section
    ]
    print("\nSupported top-section check")
    if not misses:
        print("  all supported questions retrieved the expected section")
        return

    for row in misses:
        print(
            f"  {row.case.case_id}: expected '{row.case.expected_section}', "
            f"got '{row.section}' ({row.chunk_id})"
        )


if __name__ == "__main__":
    raise SystemExit(main())
