"""Common domain models and strict types."""

import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


class StrictModel(BaseModel):
    """Base model that forbids extra fields."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )


class FrozenModel(StrictModel):
    """Base model that forbids extra fields and is immutable."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
    )


EntityId = Annotated[
    str,
    Field(pattern=r"^[a-z][a-z0-9_-]{2,63}$"),
]

SemanticVersion = Annotated[
    str,
    Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"),
]

DisplayString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]


def _ensure_utc(v: datetime.datetime) -> datetime.datetime:
    if v.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware")
    return v.astimezone(datetime.UTC)


UtcDatetime = Annotated[datetime.datetime, AfterValidator(_ensure_utc)]


class Rational(FrozenModel):
    """A rational number representing a fraction."""

    numerator: int
    denominator: int

    @model_validator(mode="after")
    def check_denominator(self) -> "Rational":
        if self.denominator == 0:
            raise ValueError("Denominator cannot be zero")
        return self
