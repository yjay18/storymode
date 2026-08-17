"""Campaign source importers package (BUILD-02)."""

from campaign.importers.compactor import (
    ConsolidatedArea,
    ConsolidatedEntity,
    CulturalProfile,
    SourceCompactor,
    WorldCodex,
)
from campaign.importers.epub import EPUBImporter
from campaign.importers.errors import (
    FileTooLargeError,
    InvalidEncodingError,
    SecurityViolationError,
    SourceImportError,
    UnsupportedFormatError,
)
from campaign.importers.plain_text import (
    DEFAULT_CHUNK_CHARS,
    MAX_SOURCE_BYTES,
    ImportedDocument,
    PlainTextImporter,
    SourceChunk,
)

__all__ = [
    "DEFAULT_CHUNK_CHARS",
    "MAX_SOURCE_BYTES",
    "ConsolidatedArea",
    "ConsolidatedEntity",
    "CulturalProfile",
    "EPUBImporter",
    "FileTooLargeError",
    "ImportedDocument",
    "InvalidEncodingError",
    "PlainTextImporter",
    "SecurityViolationError",
    "SourceChunk",
    "SourceCompactor",
    "SourceImportError",
    "UnsupportedFormatError",
    "WorldCodex",
]
