"""Unit tests for PlainTextImporter (BUILD-02)."""

from pathlib import Path

import pytest

from campaign.importers import (
    FileTooLargeError,
    InvalidEncodingError,
    PlainTextImporter,
    UnsupportedFormatError,
)


def test_import_plain_text_success(tmp_path: Path) -> None:
    text_file = tmp_path / "lore.txt"
    content = (
        "Chapter 1: The Northern Border\n\n"
        "The snow fell heavily upon the stone walls.\n\n"
        "Chapter 2: The Hearth\n\n"
        "A warm fire burned in the tavern."
    )
    text_file.write_text(content, encoding="utf-8")

    importer = PlainTextImporter(chunk_chars=100)
    doc = importer.import_file(text_file)

    assert doc.title == "lore"
    assert doc.source_type == "plain_text"
    assert doc.total_chars > 0
    assert len(doc.chunks) >= 1


def test_import_unsupported_format(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.docx"
    bad_file.write_text("hello")

    importer = PlainTextImporter()
    with pytest.raises(UnsupportedFormatError):
        importer.import_file(bad_file)


def test_import_non_existent_file() -> None:
    importer = PlainTextImporter()
    with pytest.raises(FileNotFoundError):
        importer.import_file("does_not_exist.txt")


def test_import_rejects_binary_nul() -> None:
    importer = PlainTextImporter()
    with pytest.raises(InvalidEncodingError):
        importer.import_bytes(b"hello\x00world")


def test_import_file_too_large() -> None:
    importer = PlainTextImporter(max_bytes=50)
    with pytest.raises(FileTooLargeError):
        importer.import_bytes(b"A" * 100)
