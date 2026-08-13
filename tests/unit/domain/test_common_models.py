"""Tests for common domain models and strict types."""

import datetime
import math

import pytest
from pydantic import BaseModel, ValidationError

from domain.models.common import (
    DisplayString,
    EntityId,
    Rational,
    SemanticVersion,
    StrictModel,
    UtcDatetime,
)
from domain.models.diagnostics import Diagnostic


class DummyStrict(StrictModel):
    field: int
    id_val: EntityId
    version: SemanticVersion
    text: DisplayString
    dt: UtcDatetime
    ratio: Rational


def test_strict_model_valid() -> None:
    """Valid boundaries parse correctly."""
    dt = datetime.datetime.now(datetime.UTC)
    model = DummyStrict(
        field=42,
        id_val="valid-id-123",
        version="1.0.0",
        text="A valid string",
        dt=dt,
        ratio=Rational(numerator=1, denominator=2),
    )
    assert model.field == 42
    assert model.id_val == "valid-id-123"
    assert model.version == "1.0.0"
    assert model.text == "A valid string"
    assert model.dt == dt
    assert model.ratio.numerator == 1
    assert model.ratio.denominator == 2


def test_strict_model_rejects_bool_for_int() -> None:
    """Reject bool where an integer is required."""
    with pytest.raises(ValidationError) as exc:
        DummyStrict(
            field=True,
            id_val="valid",
            version="1.0.0",
            text="text",
            dt=datetime.datetime.now(datetime.UTC),
            ratio=Rational(numerator=1, denominator=2),
        )
    assert "Input should be a valid integer" in str(exc.value)


def test_strict_model_rejects_extra_fields() -> None:
    """Reject extra fields."""
    with pytest.raises(ValidationError) as exc:
        DummyStrict(
            field=42,
            id_val="valid",
            version="1.0.0",
            text="text",
            dt=datetime.datetime.now(datetime.UTC),
            ratio=Rational(numerator=1, denominator=2),
            extra_field="bad",
        )  # type: ignore
    assert "Extra inputs are not permitted" in str(exc.value)


def test_entity_id_boundaries() -> None:
    """Test valid and bad IDs."""

    class IdModel(BaseModel):
        id_val: EntityId

    # Valid
    IdModel(id_val="a-b_c123")
    IdModel(id_val="abc")
    IdModel(id_val="a" + "b" * 63)

    # Invalid
    with pytest.raises(ValidationError):
        IdModel(id_val="1abc")  # starts with number
    with pytest.raises(ValidationError):
        IdModel(id_val="ab")  # too short
    with pytest.raises(ValidationError):
        IdModel(id_val="a" + "b" * 64)  # too long
    with pytest.raises(ValidationError):
        IdModel(id_val="Abc")  # uppercase
    with pytest.raises(ValidationError):
        IdModel(id_val="a b")  # space


def test_display_string_whitespace() -> None:
    """Test whitespace-only text is rejected and strings are trimmed."""

    class TextModel(BaseModel):
        text: DisplayString

    # Valid
    m = TextModel(text="  hello  ")
    assert m.text == "hello"  # trimmed

    # Invalid (empty after strip)
    with pytest.raises(ValidationError):
        TextModel(text="   ")

    # Invalid (too long)
    with pytest.raises(ValidationError):
        TextModel(text="a" * 121)


def test_naive_timestamps() -> None:
    """Naive timestamps must be rejected."""

    class DtModel(BaseModel):
        dt: UtcDatetime

    # Valid aware
    DtModel(dt=datetime.datetime.now(datetime.UTC))

    # Invalid naive
    with pytest.raises(ValidationError):
        DtModel(dt=datetime.datetime.now())  # noqa: DTZ005


def test_rational_zero_denominator() -> None:
    """Zero denominator is rejected."""
    with pytest.raises(ValidationError):
        Rational(numerator=1, denominator=0)


def test_non_finite_numeric_values() -> None:
    """Non-finite or float values where int is required fail."""
    with pytest.raises(ValidationError):
        Rational(numerator=math.inf, denominator=1)  # type: ignore
    with pytest.raises(ValidationError):
        Rational(numerator=math.nan, denominator=1)  # type: ignore
    with pytest.raises(ValidationError):
        Rational(numerator=1.5, denominator=1)  # type: ignore


def test_frozen_model_is_immutable() -> None:
    """Frozen model rejects modification."""
    r = Rational(numerator=1, denominator=2)
    with pytest.raises(ValidationError):
        r.numerator = 3  # type: ignore[misc]


def test_diagnostic_sort_key() -> None:
    """Diagnostic sort key is stable."""
    d1 = Diagnostic(file="a.json", json_pointer="/a", code="ERR1", message="A")
    d2 = Diagnostic(file="a.json", json_pointer="/a", code="ERR2", message="A")
    d3 = Diagnostic(file="b.json", json_pointer="/a", code="ERR1", message="A")
    d4 = Diagnostic(file="a.json", json_pointer="/a", code="ERR1", message="B")

    lst = [d3, d2, d4, d1]
    lst.sort()

    assert lst == [d1, d4, d2, d3]
