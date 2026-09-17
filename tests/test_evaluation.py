"""Offline checks for the inspectable retrieval evaluation data."""

import json
from pathlib import Path

from scripts.evaluate_retrieval import (
    EXPECTED_CATEGORY_COUNTS,
    SUPPORTED_CATEGORIES,
    _load_cases,
)


QUESTIONS_PATH = Path("evaluation/questions.json")


def test_evaluation_question_counts_and_supported_sections() -> None:
    cases = _load_cases(QUESTIONS_PATH)

    actual_counts = {
        category: sum(case.category == category for case in cases)
        for category in EXPECTED_CATEGORY_COUNTS
    }
    assert actual_counts == EXPECTED_CATEGORY_COUNTS
    assert all(
        case.expected_section is not None
        for case in cases
        if case.category in SUPPORTED_CATEGORIES
    )


def test_three_manual_adversarial_cases_are_defined() -> None:
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    manual_cases = data["manual_rag_questions"]

    assert {case["id"] for case in manual_cases} == {
        "false_premise",
        "prompt_injection",
        "mixed_supported_unsupported",
    }
    assert all(case["question"] for case in manual_cases)
    assert all(case["expected_behavior"] for case in manual_cases)
