"""Errors for state operations."""

class SaveError(Exception):
    """Base class for save operations."""
    pass


class CorruptSaveError(SaveError):
    """Raised when save data is malformed or invalid."""
    pass


class UnsafePathError(SaveError):
    """Raised when a save path is outside the allowed root."""
    pass


class CampaignMismatchError(SaveError):
    """Raised when the save belongs to a different campaign or fingerprint."""
    pass


class StaleRevisionError(SaveError):
    """Raised when expected revision does not match current state."""
    pass


class IdempotentCommandError(SaveError):
    """Raised when command payload conflicts with a previously executed command."""
    pass
