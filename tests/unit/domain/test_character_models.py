"""Tests for character and companion models."""

from typing import Any

import pytest
from pydantic import ValidationError

from domain.models.character import (
    BackgroundDefinition,
    CharactersFile,
    CompanionDefinition,
    StatBlock,
)


def make_valid_stat_block() -> dict[str, Any]:
    return {
        "strength": 10,
        "dexterity": 12,
        "intelligence": 14,
        "charisma": 8,
        "constitution": 10,
        "wisdom": 16,
    }


def make_valid_companion(cid: str = "comp-1") -> dict[str, Any]:
    return {
        "id": cid,
        "name": "A Companion",
        "role": "Fighter",
        "home_area_id": "area-1",
        "knowledge_tags": [],
        "goal": "Revenge",
        "interaction_hooks": [],
        "combat_role": "Tank",
        "base_stats": make_valid_stat_block(),
        "skill_tree_id": "tree-1",
        "starting_skill_ids": ["skill-1", "skill-2"],
        "starting_loadout": ["skill-1"],
        "relationship_rules": [],
        "story_hook_ids": [],
        "availability_rules": [],
        "minimum_usable_actions": 2,
    }


def test_stat_block_exact_six() -> None:
    data = make_valid_stat_block()

    # Missing stat
    del data["strength"]
    with pytest.raises(ValidationError):
        StatBlock(**data)

    # Extra stat
    data["strength"] = 10
    data["extra"] = 10
    with pytest.raises(ValidationError):
        StatBlock(**data)


def test_stat_block_out_of_range() -> None:
    data = make_valid_stat_block()

    # Stat too low
    data["strength"] = 0
    with pytest.raises(ValidationError):
        StatBlock(**data)

    # Stat too high
    data["strength"] = 31
    with pytest.raises(ValidationError):
        StatBlock(**data)


def test_background_bonus_range() -> None:
    with pytest.raises(ValidationError):
        BackgroundDefinition(
            **{  # type: ignore
                "id": "bg-1",
                "name": "Bg",
                "description": "Desc",
                "stat_bonus": "strength",
                "stat_bonus_value": 3,  # Invalid
                "starting_skill_ids": [],
                "starting_item_ids": [],
                "starting_fact_ids": [],
            }
        )


def test_companion_loadout_rules() -> None:
    data = make_valid_companion()

    # Unknown skill
    data["starting_loadout"] = ["skill-3"]
    with pytest.raises(ValidationError) as exc:
        CompanionDefinition(**data)
    assert "not known" in str(exc.value)

    # Duplicate skill
    data["starting_loadout"] = ["skill-1", "skill-1"]
    with pytest.raises(ValidationError) as exc:
        CompanionDefinition(**data)
    assert "duplicate skills" in str(exc.value)

    # Fifth skill (too many)
    data["starting_skill_ids"] = ["sk-1", "sk-2", "sk-3", "sk-4", "sk-5"]
    data["starting_loadout"] = ["sk-1", "sk-2", "sk-3", "sk-4", "sk-5"]
    with pytest.raises(ValidationError) as exc:
        CompanionDefinition(**data)
    assert "exceed four" in str(exc.value)


def test_companion_usable_actions_bounds() -> None:
    data = make_valid_companion()

    # Too low
    data["minimum_usable_actions"] = 0
    with pytest.raises(ValidationError):
        CompanionDefinition(**data)

    # Too high
    data["minimum_usable_actions"] = 5
    with pytest.raises(ValidationError):
        CompanionDefinition(**data)


def test_characters_file_duplicate_ids() -> None:
    data = {
        "campaign_id": "test",
        "campaign_version": "1.0.0",
        "protagonist_backgrounds": [],
        "major_npcs": [],
        "companions": [
            make_valid_companion("comp-1"),
            make_valid_companion("comp-1"),
        ],
    }
    with pytest.raises(ValidationError) as exc:
        CharactersFile(**data)  # type: ignore
    assert "duplicate character IDs found" in str(exc.value)
