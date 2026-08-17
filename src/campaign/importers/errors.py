"""Typed error hierarchy for campaign source importers (BUILD-02)."""

from __future__ import annotations


class SourceImportError(Exception):
    """Base exception for source import errors."""


class FileTooLargeError(SourceImportError):
    """Raised when an imported source file exceeds the maximum byte limit."""


class UnsupportedFormatError(SourceImportError):
    """Raised when an imported source format or extension is not supported."""


class InvalidEncodingError(SourceImportError):
    """Raised when an imported file contains non-UTF-8 or invalid control characters."""


class SecurityViolationError(SourceImportError):
    """Raised when an imported archive violates security bounds (e.g. zip-slip, symlink)."""
