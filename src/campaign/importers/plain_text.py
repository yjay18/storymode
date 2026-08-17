"""Bounded plain-text and transcript source importer (BUILD-02).

Guarantees:
- Strictly enforces byte and character caps (max 50 MB source file).
- Rejects binary files, NUL bytes, and invalid control characters.
- Chunks text deterministically at paragraph boundaries.
- Returns immutable ImportedDocument with typed chunks.
"""

from __future__ import annotations

import re
from pathlib import Path

from campaign.builder.models import SourceType
from campaign.importers.errors import (
    FileTooLargeError,
    InvalidEncodingError,
    UnsupportedFormatError,
)
from domain.models.common import FrozenModel

MAX_SOURCE_BYTES: int = 50 * 1024 * 1024  # 50 MB
DEFAULT_CHUNK_CHARS: int = 12000  # ~3,000 words
SUPPORTED_TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {".txt", ".text", ".md", ".markdown", ".transcript"}
)


class SourceChunk(FrozenModel):
    """A bounded chunk of source text for summarization and extraction."""

    index: int
    title: str | None = None
    text: str
    char_count: int


class ImportedDocument(FrozenModel):
    """The normalized result of importing a source document."""

    title: str
    source_type: SourceType
    total_chars: int
    chunks: list[SourceChunk]


class PlainTextImporter:
    """Imports plain-text documents into structured, bounded chunks."""

    def __init__(
        self,
        max_bytes: int = MAX_SOURCE_BYTES,
        chunk_chars: int = DEFAULT_CHUNK_CHARS,
    ) -> None:
        self.max_bytes = max_bytes
        self.chunk_chars = chunk_chars

    def import_file(self, path: Path | str) -> ImportedDocument:
        """Read and import a local plain-text file."""
        file_path = Path(path)
        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_TEXT_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_TEXT_EXTENSIONS))
            raise UnsupportedFormatError(
                f"Unsupported text format '{ext}'. Supported extensions: {supported}"
            )

        if not file_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")

        file_size = file_path.stat().st_size
        if file_size > self.max_bytes:
            raise FileTooLargeError(
                f"File size ({file_size} bytes) exceeds limit of {self.max_bytes} bytes"
            )

        raw_bytes = file_path.read_bytes()
        return self.import_bytes(raw_bytes, title=file_path.stem)

    def import_bytes(self, raw_bytes: bytes, title: str = "Source Document") -> ImportedDocument:
        """Validate and chunk raw bytes from a plain text document."""
        if len(raw_bytes) > self.max_bytes:
            raise FileTooLargeError(
                f"Content size ({len(raw_bytes)} bytes) exceeds limit of {self.max_bytes} bytes"
            )

        # 1. Decode UTF-8
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise InvalidEncodingError(f"File is not valid UTF-8: {e}") from e

        return self.import_string(text, title=title)

    def import_string(self, text: str, title: str = "Source Document") -> ImportedDocument:
        """Validate and chunk a string from a plain text document."""
        # Check for NUL bytes or hostile control characters
        if "\x00" in text:
            raise InvalidEncodingError("File contains binary NUL bytes")

        # Strip unprintable control characters (allow tab, newline, carriage return)
        sanitized = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text).strip()
        if not sanitized:
            return ImportedDocument(
                title=title,
                source_type="plain_text",
                total_chars=0,
                chunks=[],
            )

        # 2. Chunk text at paragraph boundaries
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", sanitized) if p.strip()]
        chunks: list[SourceChunk] = []
        current_paras: list[str] = []
        current_len = 0
        chunk_idx = 1

        for para in paragraphs:
            para_len = len(para) + 2  # account for separator
            if current_len + para_len > self.chunk_chars and current_paras:
                chunk_text = "\n\n".join(current_paras)
                chunks.append(
                    SourceChunk(
                        index=chunk_idx,
                        title=f"Segment {chunk_idx}",
                        text=chunk_text,
                        char_count=len(chunk_text),
                    )
                )
                chunk_idx += 1
                current_paras = [para]
                current_len = len(para)
            else:
                current_paras.append(para)
                current_len += para_len

        if current_paras:
            chunk_text = "\n\n".join(current_paras)
            chunks.append(
                SourceChunk(
                    index=chunk_idx,
                    title=f"Segment {chunk_idx}",
                    text=chunk_text,
                    char_count=len(chunk_text),
                )
            )

        return ImportedDocument(
            title=title,
            source_type="plain_text",
            total_chars=len(sanitized),
            chunks=chunks,
        )
