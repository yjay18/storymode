"""Tests for enemy models."""

from typing import Any

import pytest
from pydantic import ValidationError

from domain.models.enemy import EnemyArchetype, LootEntry


def make_valid_loot() -> dict[str, Any]:
    return {
        "item_id": "item-1",
        "minimum_quantity": 1,
        "maximum_quantity": 5,
        "weight": 10,
    }


def make_valid_enemy() -> dict[str, Any]:
    return {
        "id": "enemy-1",
        "name": "Goblin",
        "description": "A small goblin",
        "base_hp": 10,
        "base_armour": 0,
        "speed": 10,
        "dexterity": 10,
        "base_mana": 0,
        "mana_regen": 0,
        "combat_skill_ids": ["skill-1"],
        "behavior_profile": "Aggressive",
        "escape_policy_id": "flee-1",
        "power_rating": 10,
        "loot_table": [make_valid_loot()],
        "portrait_prompt": "Goblin",
        "art_style_ref": "Dark fantasy",
    }


def test_loot_weight_and_quantity() -> None:
    data = make_valid_loot()

    # Invalid weight
    data["weight"] = 0
    with pytest.raises(ValidationError):
        LootEntry(**data)

    # Invalid quantity (max < min)
    data["weight"] = 10
    data["maximum_quantity"] = 0
    with pytest.raises(ValidationError) as exc:
        LootEntry(**data)
    assert "cannot be less than minimum_quantity" in str(exc.value)


def test_enemy_bounds() -> None:
    data = make_valid_enemy()

    # HP out of bounds
    data["base_hp"] = 0
    with pytest.raises(ValidationError):
        EnemyArchetype(**data)

    data["base_hp"] = 10001
    with pytest.raises(ValidationError):
        EnemyArchetype(**data)
    data["base_hp"] = 10

    # Armour out of bounds
    data["base_armour"] = -1
    with pytest.raises(ValidationError):
        EnemyArchetype(**data)
    data["base_armour"] = 10001
    with pytest.raises(ValidationError):
        EnemyArchetype(**data)
    data["base_armour"] = 0

    # Speed out of bounds
    data["speed"] = -1
    with pytest.raises(ValidationError):
        EnemyArchetype(**data)
    data["speed"] = 101
    with pytest.raises(ValidationError):
        EnemyArchetype(**data)


def test_enemy_missing_action() -> None:
    data = make_valid_enemy()
    data["combat_skill_ids"] = []
    with pytest.raises(ValidationError):
        EnemyArchetype(**data)
