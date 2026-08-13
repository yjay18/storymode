"""Diagnostic models for schema and validation errors."""

from typing import Any

from pydantic import Field

from domain.models.common import FrozenModel


class Diagnostic(FrozenModel):
    """A diagnostic message with a stable sort key."""

    code: str
    file: str | None = None
    json_pointer: str
    message: str
    related_ids: list[str] = Field(default_factory=list)

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Diagnostic):
            return NotImplemented
        return (
            self.file or "",
            self.json_pointer,
            self.code,
            self.message,
        ) < (
            other.file or "",
            other.json_pointer,
            other.code,
            other.message,
        )
