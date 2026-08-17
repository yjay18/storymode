"""Zero-dependency EPUB source importer (BUILD-02).

Guarantees:
- Uses Python standard library only (zipfile, xml.etree.ElementTree, html.parser).
- Enforces strict zip-bomb (max uncompressed size) and path traversal defenses.
- Reads META-INF/container.xml and OPF package spine for true reading order.
- Extracts clean chapter titles and text, stripping scripts, styles, and markup.
- Produces immutable ImportedDocument with chapter-bounded SourceChunks.
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

from campaign.importers.errors import (
    FileTooLargeError,
    InvalidEncodingError,
    SecurityViolationError,
    UnsupportedFormatError,
)
from campaign.importers.plain_text import (
    DEFAULT_CHUNK_CHARS,
    ImportedDocument,
    SourceChunk,
)

MAX_EPUB_BYTES: int = 100 * 1024 * 1024  # 100 MB archive
MAX_UNCOMPRESSED_BYTES: int = 250 * 1024 * 1024  # 250 MB decompressed limit


class _HTMLTextExtractor(HTMLParser):
    """Simple, safe HTML/XHTML parser that extracts chapter headings and clean text."""

    def __init__(self) -> None:
        super().__init__()
        self._text_parts: list[str] = []
        self._heading_parts: list[str] = []
        self._in_script = False
        self._in_style = False
        self._in_heading = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "nav"):
            self._in_script = True
        elif tag_lower in ("h1", "h2", "h3", "title"):
            self._in_heading = True

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "nav"):
            self._in_script = False
        elif tag_lower in ("h1", "h2", "h3", "title"):
            self._in_heading = False
        elif tag_lower in ("p", "div", "br", "li", "tr", "blockquote"):
            self._text_parts.append("\n\n")

    def handle_data(self, data: str) -> None:
        if self._in_script:
            return
        clean = data.strip()
        if not clean:
            return
        if self._in_heading:
            self._heading_parts.append(clean)
        self._text_parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._text_parts)
        # Normalize double newlines
        lines = [line.strip() for line in raw.split("\n")]
        non_empty = []
        for line in lines:
            if line:
                non_empty.append(line)
        return "\n\n".join(non_empty)

    def get_heading(self) -> str | None:
        heading = " ".join(self._heading_parts).strip()
        return heading if heading else None


class EPUBImporter:
    """Imports EPUB digital books into structured, chapter-bounded chunks."""

    def __init__(
        self,
        max_bytes: int = MAX_EPUB_BYTES,
        max_uncompressed_bytes: int = MAX_UNCOMPRESSED_BYTES,
        chunk_chars: int = DEFAULT_CHUNK_CHARS,
    ) -> None:
        self.max_bytes = max_bytes
        self.max_uncompressed_bytes = max_uncompressed_bytes
        self.chunk_chars = chunk_chars

    def import_file(self, path: Path | str) -> ImportedDocument:
        """Read and import an EPUB file."""
        file_path = Path(path)
        if file_path.suffix.lower() != ".epub":
            raise UnsupportedFormatError(f"Expected .epub file, got '{file_path.suffix}'")

        if not file_path.exists():
            raise FileNotFoundError(f"EPUB file not found: {file_path}")

        file_size = file_path.stat().st_size
        if file_size > self.max_bytes:
            raise FileTooLargeError(
                f"EPUB size ({file_size} bytes) exceeds limit of {self.max_bytes} bytes"
            )

        raw_bytes = file_path.read_bytes()
        return self.import_bytes(raw_bytes, default_title=file_path.stem)

    def import_bytes(
        self, raw_bytes: bytes, default_title: str = "Imported Novel"
    ) -> ImportedDocument:
        """Validate, extract, and chunk raw EPUB archive bytes."""
        if len(raw_bytes) > self.max_bytes:
            raise FileTooLargeError(
                f"EPUB size ({len(raw_bytes)} bytes) exceeds limit of {self.max_bytes} bytes"
            )

        try:
            zf = zipfile.ZipFile(io.BytesIO(raw_bytes))
        except zipfile.BadZipFile as e:
            raise InvalidEncodingError(f"Invalid EPUB zip container: {e}") from e

        # 1. Zip bomb & path traversal verification
        total_uncompressed = 0
        for info in zf.infolist():
            total_uncompressed += info.file_size
            if total_uncompressed > self.max_uncompressed_bytes:
                raise FileTooLargeError(
                    f"Decompressed EPUB size exceeds safety limit of "
                    f"{self.max_uncompressed_bytes} bytes"
                )
            if info.filename.startswith("/") or ".." in info.filename:
                raise SecurityViolationError(f"Illegal zip entry path: {info.filename}")

        # 2. Locate root OPF package file via container.xml
        try:
            container_xml = zf.read("META-INF/container.xml")
        except KeyError as e:
            raise UnsupportedFormatError("Missing META-INF/container.xml in EPUB") from e

        try:
            root_tree = ET.fromstring(container_xml)
            # xmlns usually urn:oasis:names:tc:opendocument:xmlns:container
            rootfile_el = root_tree.find(".//{*}rootfile")
            if rootfile_el is None or "full-path" not in rootfile_el.attrib:
                raise UnsupportedFormatError("No valid rootfile found in EPUB container.xml")
            opf_path = rootfile_el.attrib["full-path"]
        except ET.ParseError as e:
            raise InvalidEncodingError(f"Malformed container.xml: {e}") from e

        # 3. Read OPF manifest and spine
        try:
            opf_bytes = zf.read(opf_path)
            opf_tree = ET.fromstring(opf_bytes)
        except (KeyError, ET.ParseError) as e:
            raise UnsupportedFormatError(f"Failed to read OPF file '{opf_path}': {e}") from e

        opf_dir = str(PurePosixPath(opf_path).parent)
        if opf_dir == ".":
            opf_dir = ""

        # Extract title from metadata if present
        title_el = opf_tree.find(".//{*}metadata/{*}title")
        book_title = (
            title_el.text.strip() if title_el is not None and title_el.text else default_title
        )

        # Map item IDs to hrefs
        manifest_items: dict[str, str] = {}
        for item in opf_tree.findall(".//{*}manifest/{*}item"):
            item_id = item.attrib.get("id")
            href = item.attrib.get("href")
            if item_id and href:
                # Resolve relative to opf_dir
                full_href = f"{opf_dir}/{href}".lstrip("/") if opf_dir else href
                manifest_items[item_id] = full_href

        # Extract spine order
        spine_hrefs: list[str] = []
        for itemref in opf_tree.findall(".//{*}spine/{*}itemref"):
            idref = itemref.attrib.get("idref")
            if idref and idref in manifest_items:
                spine_hrefs.append(manifest_items[idref])

        # 4. Extract chapters in spine order
        chunks: list[SourceChunk] = []
        chunk_idx = 1
        total_chars = 0

        for href in spine_hrefs:
            try:
                chapter_bytes = zf.read(href)
                chapter_html = chapter_bytes.decode("utf-8", errors="replace")
            except KeyError:
                continue

            parser = _HTMLTextExtractor()
            parser.feed(chapter_html)
            chapter_text = parser.get_text()
            if not chapter_text:
                continue

            chapter_heading = parser.get_heading() or f"Chapter {chunk_idx}"
            total_chars += len(chapter_text)

            # If chapter is within chunk_chars, add directly
            if len(chapter_text) <= self.chunk_chars:
                chunks.append(
                    SourceChunk(
                        index=chunk_idx,
                        title=chapter_heading,
                        text=chapter_text,
                        char_count=len(chapter_text),
                    )
                )
                chunk_idx += 1
            else:
                # Split large chapter into sub-parts
                paras = chapter_text.split("\n\n")
                current_sub: list[str] = []
                curr_len = 0
                part_idx = 1

                for p in paras:
                    if curr_len + len(p) + 2 > self.chunk_chars and current_sub:
                        sub_text = "\n\n".join(current_sub)
                        chunks.append(
                            SourceChunk(
                                index=chunk_idx,
                                title=f"{chapter_heading} (Part {part_idx})",
                                text=sub_text,
                                char_count=len(sub_text),
                            )
                        )
                        chunk_idx += 1
                        part_idx += 1
                        current_sub = [p]
                        curr_len = len(p)
                    else:
                        current_sub.append(p)
                        curr_len += len(p) + 2

                if current_sub:
                    sub_text = "\n\n".join(current_sub)
                    chunks.append(
                        SourceChunk(
                            index=chunk_idx,
                            title=f"{chapter_heading} (Part {part_idx})",
                            text=sub_text,
                            char_count=len(sub_text),
                        )
                    )
                    chunk_idx += 1

        return ImportedDocument(
            title=book_title,
            source_type="epub",
            total_chars=total_chars,
            chunks=chunks,
        )
