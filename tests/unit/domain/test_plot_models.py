"""Tests for plot models."""

from typing import Any

import pytest
from pydantic import ValidationError

from domain.models.plot import ClockDefinition, ClockVisibility


def make_valid_clock() -> dict[str, Any]:
    return {
        "id": "clock-1",
        "name": "Impending Doom",
        "maximum": 6,
        "visibility": ClockVisibility.PUBLIC,
        "trigger_event_types": ["failed_stealth"],
        "completion_effect_ids": [],
    }


def test_clock_limits() -> None:
    data = make_valid_clock()

    # Valid
    ClockDefinition(**data)

    # Too small
    data["maximum"] = 2
    with pytest.raises(ValidationError):
        ClockDefinition(**data)

    # Too large
    data["maximum"] = 13
    with pytest.raises(ValidationError):
        ClockDefinition(**data)
