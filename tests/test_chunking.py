"""Tests for deterministic, section-aware token chunking."""

from dataclasses import asdict

import tiktoken

from app.chunking import (
    CHUNK_OVERLAP_TOKENS,
    TARGET_CHUNK_TOKENS,
    TOKEN_ENCODING_NAME,
    chunk_document,
)
from app.document_loader import LoadedDocument


ENCODING = tiktoken.get_encoding(TOKEN_ENCODING_NAME)


def _document(
    text: str,
    *,
    source: str = "synthetic.md",
    extension: str = ".md",
) -> LoadedDocument:
    return LoadedDocument(text=text, source=source, extension=extension)


def test_same_input_produces_identical_chunks() -> None:
    document = _document(
        "# Synthetic Section\n\n" + "Synthetic sentence. " * 300
    )

    first = chunk_document(document)
    second = chunk_document(document)

    assert first == second


def test_chunk_ids_are_predictable() -> None:
    document = _document(
        "# First\n\nSynthetic one.\n\n"
        "## Second\n\nSynthetic two.\n\n"
        "### Third\n\nSynthetic three."
    )

    chunks = chunk_document(document)

    assert [chunk.chunk_id for chunk in chunks] == [
        "chunk_0001",
        "chunk_0002",
        "chunk_0003",
    ]


def test_generated_chunks_never_have_empty_text() -> None:
    document = _document(
        "# Empty Synthetic Section\n\n"
        "## Section With Content\n\nSynthetic content."
    )

    chunks = chunk_document(document)

    assert chunks
    assert all(chunk.text.strip() for chunk in chunks)


def test_short_section_remains_one_chunk() -> None:
    document = _document(
        "## Synthetic Short Section\n\nThis short section stays together."
    )

    chunks = chunk_document(document)

    assert len(chunks) == 1
    assert chunks[0].section == "Synthetic Short Section"
    assert chunks[0].text == "This short section stays together."


def test_long_section_is_split_into_multiple_chunks() -> None:
    paragraphs = ["synthetic " * 120 for _ in range(8)]
    document = _document("# Synthetic Long Section\n\n" + "\n\n".join(paragraphs))

    chunks = chunk_document(document)

    assert len(chunks) > 1
    assert all(chunk.section == "Synthetic Long Section" for chunk in chunks)


def test_paragraph_aware_splitting_includes_overlap() -> None:
    paragraphs = ["synthetic " * 45 for _ in range(4)]
    document = _document("# Overlap Example\n\n" + "\n\n".join(paragraphs))

    chunks = chunk_document(document, target_tokens=80, overlap_tokens=15)

    assert len(chunks) > 1
    expected_overlap = ENCODING.decode(ENCODING.encode(chunks[0].text)[-15:])
    assert chunks[1].text.startswith(expected_overlap)


def test_oversized_paragraph_uses_exact_token_windows() -> None:
    paragraph = " ".join(f"synthetic{index}" for index in range(200))
    document = _document(paragraph)
    target_tokens = 40
    overlap_tokens = 8
    token_ids = ENCODING.encode(paragraph)
    expected_windows: list[str] = []
    start = 0

    while start < len(token_ids):
        end = min(start + target_tokens, len(token_ids))
        expected_windows.append(ENCODING.decode(token_ids[start:end]))
        if end == len(token_ids):
            break
        start = end - overlap_tokens

    chunks = chunk_document(
        document,
        target_tokens=target_tokens,
        overlap_tokens=overlap_tokens,
    )

    assert [chunk.text for chunk in chunks] == expected_windows


def test_markdown_heading_metadata_is_preserved() -> None:
    document = _document(
        "# Synthetic Parent\n\nParent content.\n\n"
        "### Synthetic Child ###\n\nChild content."
    )

    chunks = chunk_document(document)

    assert [chunk.section for chunk in chunks] == [
        "Synthetic Parent",
        "Synthetic Child",
    ]


def test_content_before_first_heading_has_no_section() -> None:
    document = _document(
        "Synthetic introductory content.\n\n"
        "# Named Section\n\nSynthetic section content."
    )

    chunks = chunk_document(document)

    assert chunks[0].section is None
    assert chunks[0].text == "Synthetic introductory content."
    assert chunks[1].section == "Named Section"


def test_plain_text_without_headings_can_be_chunked() -> None:
    text = "# This is plain text, not Markdown metadata.\n\nSynthetic body."
    document = _document(text, source="synthetic.txt", extension=".txt")

    chunks = chunk_document(document)

    assert len(chunks) == 1
    assert chunks[0].source == "synthetic.txt"
    assert chunks[0].section is None
    assert chunks[0].text == text


def test_stored_token_counts_match_the_configured_tokenizer() -> None:
    document = _document(
        "# Token Count Example\n\n" + "Synthetic token-count text. " * 300
    )

    chunks = chunk_document(document)

    assert all(
        chunk.token_count == len(ENCODING.encode(chunk.text)) for chunk in chunks
    )


def test_all_chunk_fields_remain_stable_across_runs() -> None:
    assert TARGET_CHUNK_TOKENS == 450
    assert CHUNK_OVERLAP_TOKENS == 75
    document = _document(
        "Synthetic preface.\n\n"
        "# Stable Section\n\n"
        + "Stable synthetic paragraph. " * 300
    )

    first = [asdict(chunk) for chunk in chunk_document(document)]
    second = [asdict(chunk) for chunk in chunk_document(document)]

    assert first == second
