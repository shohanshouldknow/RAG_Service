"""Tests for safe local document loading."""

from pathlib import Path

import pytest

from app.document_loader import DocumentLoadError, load_document


def test_markdown_file_loads_successfully(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.md"
    path.write_text("# Synthetic Heading\n\nSynthetic content.", encoding="utf-8")

    document = load_document(path)

    assert document.source == "synthetic.md"
    assert document.extension == ".md"
    assert document.text == "# Synthetic Heading\n\nSynthetic content."


def test_text_file_loads_successfully(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.txt"
    path.write_text("Synthetic plain-text content.", encoding="utf-8")

    document = load_document(path)

    assert document.source == "synthetic.txt"
    assert document.extension == ".txt"
    assert document.text == "Synthetic plain-text content."


def test_missing_file_fails_clearly(tmp_path: Path) -> None:
    path = tmp_path / "missing.md"

    with pytest.raises(DocumentLoadError, match="does not exist"):
        load_document(path)


def test_directory_path_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(DocumentLoadError, match="not a file"):
        load_document(tmp_path)


def test_unsupported_extension_fails_clearly(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.pdf"
    path.write_text("Synthetic content.", encoding="utf-8")

    with pytest.raises(DocumentLoadError, match="Unsupported document type"):
        load_document(path)


def test_empty_document_fails_clearly(tmp_path: Path) -> None:
    path = tmp_path / "empty.txt"
    path.write_text("  \n\t\n", encoding="utf-8")

    with pytest.raises(DocumentLoadError, match="Document is empty"):
        load_document(path)


def test_line_endings_are_normalized(tmp_path: Path) -> None:
    path = tmp_path / "line-endings.txt"
    path.write_bytes(b"first line\r\nsecond line\rthird line\n")

    document = load_document(path)

    assert document.text == "first line\nsecond line\nthird line"


def test_non_utf8_document_fails_clearly(tmp_path: Path) -> None:
    path = tmp_path / "invalid.txt"
    path.write_bytes(b"\xff\xfe")

    with pytest.raises(DocumentLoadError, match="UTF-8"):
        load_document(path)
