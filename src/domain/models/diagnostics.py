"""Diagnostic models for schema and validation errors."""

from typing import Any

from domain.models.common import FrozenModel


class Diagnostic(FrozenModel):
    """A diagnostic message with a stable sort key."""

    pointer: str
    code: str
    message: str

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Diagnostic):
            return NotImplemented
        return (self.pointer, self.code, self.message) < (
            other.pointer,
            other.code,
            other.message,
        )
