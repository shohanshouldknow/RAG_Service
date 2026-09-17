"""Deterministic, section-aware document chunking."""

from dataclasses import dataclass
import re
from typing import Final, Sequence

import tiktoken

from app.document_loader import LoadedDocument


TOKEN_ENCODING_NAME: Final[str] = "cl100k_base"
TARGET_CHUNK_TOKENS: Final[int] = 450
CHUNK_OVERLAP_TOKENS: Final[int] = 75

_TOKENIZER = tiktoken.get_encoding(TOKEN_ENCODING_NAME)
_MARKDOWN_HEADING = re.compile(r"^ {0,3}#{1,6}[ \t]+(.+?)\s*$")
_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n+")


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    """One deterministic piece of a loaded document."""

    chunk_id: str
    source: str
    section: str | None
    text: str
    token_count: int


@dataclass(frozen=True, slots=True)
class _DocumentSection:
    heading: str | None
    text: str


def count_tokens(text: str) -> int:
    """Count tokens using the project's single configured tokenizer."""

    return len(_TOKENIZER.encode(text))


def chunk_document(
    document: LoadedDocument,
    *,
    target_tokens: int = TARGET_CHUNK_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> list[DocumentChunk]:
    """Split a loaded document into stable, ordered chunks."""

    _validate_chunk_settings(target_tokens, overlap_tokens)

    if document.extension == ".md":
        sections = _split_markdown_sections(document.text)
    else:
        sections = [_DocumentSection(heading=None, text=document.text.strip())]

    chunk_parts: list[tuple[str | None, str]] = []
    for section in sections:
        for text in _chunk_section(section.text, target_tokens, overlap_tokens):
            if text.strip():
                chunk_parts.append((section.heading, text))

    if not chunk_parts:
        raise ValueError("Document does not contain chunkable text.")

    return [
        DocumentChunk(
            chunk_id=f"chunk_{index:04d}",
            source=document.source,
            section=section,
            text=text,
            token_count=count_tokens(text),
        )
        for index, (section, text) in enumerate(chunk_parts, start=1)
    ]


def _validate_chunk_settings(target_tokens: int, overlap_tokens: int) -> None:
    if target_tokens <= 0:
        raise ValueError("target_tokens must be greater than zero.")
    if overlap_tokens < 0:
        raise ValueError("overlap_tokens cannot be negative.")
    if overlap_tokens >= target_tokens:
        raise ValueError("overlap_tokens must be smaller than target_tokens.")


def _split_markdown_sections(text: str) -> list[_DocumentSection]:
    sections: list[_DocumentSection] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        heading_match = _MARKDOWN_HEADING.match(line)
        if heading_match:
            _append_section(sections, current_heading, current_lines)
            current_heading = _clean_heading(heading_match.group(1))
            current_lines = []
        else:
            current_lines.append(line)

    _append_section(sections, current_heading, current_lines)
    return sections


def _append_section(
    sections: list[_DocumentSection],
    heading: str | None,
    lines: list[str],
) -> None:
    section_text = "\n".join(lines).strip()
    if section_text:
        sections.append(_DocumentSection(heading=heading, text=section_text))


def _clean_heading(heading: str) -> str:
    """Remove optional closing Markdown hashes without changing heading words."""

    return re.sub(r"[ \t]+#+[ \t]*$", "", heading).strip()


def _chunk_section(
    text: str,
    target_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    section_text = text.strip()
    if not section_text:
        return []
    if count_tokens(section_text) <= target_tokens:
        return [section_text]

    paragraphs = [
        paragraph.strip()
        for paragraph in _PARAGRAPH_BREAK.split(section_text)
        if paragraph.strip()
    ]

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if count_tokens(paragraph) > target_tokens:
            if current:
                chunks.append(current)
                paragraph = _add_overlap(current, paragraph, overlap_tokens)

            windows = _split_token_windows(
                paragraph,
                target_tokens=target_tokens,
                overlap_tokens=overlap_tokens,
            )
            chunks.extend(windows[:-1])
            current = windows[-1]
            continue

        if not current:
            current = paragraph
            continue

        candidate = f"{current}\n\n{paragraph}"
        if count_tokens(candidate) <= target_tokens:
            current = candidate
            continue

        chunks.append(current)
        current = _add_overlap(current, paragraph, overlap_tokens)

    if current:
        chunks.append(current)

    return chunks


def _add_overlap(previous: str, following: str, overlap_tokens: int) -> str:
    overlap_text = _last_token_text(previous, overlap_tokens)
    if not overlap_text:
        return following
    return f"{overlap_text}\n\n{following}"


def _last_token_text(text: str, token_count: int) -> str:
    if token_count == 0:
        return ""
    token_ids = _TOKENIZER.encode(text)
    return _decode_tokens(token_ids[-token_count:])


def _split_token_windows(
    text: str,
    *,
    target_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    token_ids = _TOKENIZER.encode(text)
    windows: list[str] = []
    start = 0

    while start < len(token_ids):
        end = min(start + target_tokens, len(token_ids))
        windows.append(_decode_tokens(token_ids[start:end]))
        if end == len(token_ids):
            break
        start = end - overlap_tokens

    return windows


def _decode_tokens(token_ids: Sequence[int]) -> str:
    return _TOKENIZER.decode(list(token_ids))
