"""Tests for item models."""

from typing import Any

import pytest
from pydantic import ValidationError

from domain.models.item import ItemDefinition, ItemRarity, ItemType


def make_valid_item() -> dict[str, Any]:
    return {
        "id": "item-1",
        "name": "Sword",
        "type": ItemType.WEAPON,
        "rarity": ItemRarity.COMMON,
        "mechanics": [],
        "requirements": [],
        "capability_tags": [],
        "stacking_key": None,
        "flavour_text": "A sharp sword.",
        "provenance": "Smith",
        "max_stack": 10,
    }


def test_unique_item_stacking() -> None:
    data = make_valid_item()

    # Valid non-unique
    ItemDefinition(**data)

    # Invalid unique with max_stack > 1
    data["rarity"] = ItemRarity.UNIQUE
    with pytest.raises(ValidationError) as exc:
        ItemDefinition(**data)
    assert "unique items must have max_stack=1" in str(exc.value)

    # Valid unique
    data["max_stack"] = 1
    ItemDefinition(**data)


def test_item_flavour_text_bounds() -> None:
    data = make_valid_item()

    # Too short
    data["flavour_text"] = ""
    with pytest.raises(ValidationError):
        ItemDefinition(**data)

    # Too long
    data["flavour_text"] = "A" * 401
    with pytest.raises(ValidationError):
        ItemDefinition(**data)
