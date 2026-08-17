"""Unit tests for EPUBImporter (BUILD-02)."""

import io
import zipfile
from pathlib import Path

import pytest

from campaign.importers import (
    EPUBImporter,
    FileTooLargeError,
    SecurityViolationError,
    UnsupportedFormatError,
)


def _build_test_epub_bytes() -> bytes:
    """Build a valid minimal EPUB in memory using zipfile."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
            <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
                <rootfiles>
                    <rootfile full-path="OEBPS/content.opf"
                              media-type="application/oebps-package+xml"/>
                </rootfiles>
            </container>""",
        )
        zf.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0"?>
            <package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
                <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
                    <dc:title>Chronicles of the Realm</dc:title>
                    <dc:creator>Master Scribe</dc:creator>
                </metadata>
                <manifest>
                    <item id="ch1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
                    <item id="ch2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
                </manifest>
                <spine>
                    <itemref idref="ch1"/>
                    <itemref idref="ch2"/>
                </spine>
            </package>""",
        )
        zf.writestr(
            "OEBPS/chapter1.xhtml",
            """<html xmlns="http://www.w3.org/1999/xhtml">
                <head><title>Chapter 1: The Outpost</title></head>
                <body>
                    <h1>Chapter 1: The Outpost</h1>
                    <p>The wind blew fierce across the jagged battlements of Winterhold.</p>
                </body>
            </html>""",
        )
        zf.writestr(
            "OEBPS/chapter2.xhtml",
            """<html xmlns="http://www.w3.org/1999/xhtml">
                <head><title>Chapter 2: The Whispering Woods</title></head>
                <body>
                    <h1>Chapter 2: The Whispering Woods</h1>
                    <p>Deep within the ancient grove, Lord Brandon drew his steel blade.</p>
                </body>
            </html>""",
        )
    return buf.getvalue()


def test_import_valid_epub() -> None:
    epub_bytes = _build_test_epub_bytes()
    importer = EPUBImporter()
    doc = importer.import_bytes(epub_bytes)

    assert doc.title == "Chronicles of the Realm"
    assert doc.source_type == "epub"
    assert len(doc.chunks) == 2
    assert "The Outpost" in str(doc.chunks[0].title)
    assert "Winterhold" in doc.chunks[0].text
    assert "Whispering Woods" in str(doc.chunks[1].title)
    assert "Lord Brandon" in doc.chunks[1].text


def test_import_epub_security_zip_slip() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../escaped.txt", "malicious payload")

    importer = EPUBImporter()
    with pytest.raises(SecurityViolationError):
        importer.import_bytes(buf.getvalue())


def test_import_epub_unsupported_format(tmp_path: Path) -> None:
    bad_file = tmp_path / "book.pdf"
    bad_file.write_text("pdf text")

    importer = EPUBImporter()
    with pytest.raises(UnsupportedFormatError):
        importer.import_file(bad_file)


def test_import_epub_decompressed_size_limit() -> None:
    epub_bytes = _build_test_epub_bytes()
    # Enforce very small decompressed limit
    importer = EPUBImporter(max_uncompressed_bytes=50)
    with pytest.raises(FileTooLargeError):
        importer.import_bytes(epub_bytes)
