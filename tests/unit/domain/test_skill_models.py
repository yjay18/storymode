"""Tests for skill, effect, tree, and fusion models."""

from typing import Any

import pytest
from pydantic import ValidationError

from domain.models.skill import (
    CombatSkill,
    EffectDefinition,
    EffectDieTable,
    EffectKind,
    FusionRecipe,
    PointBuyDefinition,
    SkillTree,
    TargetRule,
)


def make_valid_effect(eid: str = "eff-1") -> dict[str, Any]:
    return {
        "effect_id": eid,
        "kind": EffectKind.DAMAGE,
        "magnitude": 10,
    }


def make_valid_level(lvl: int) -> dict[str, Any]:
    return {
        "level": lvl,
        "mana_cost": 2,
        "target_rule": TargetRule.SINGLE_ENEMY,
        "base_effects": [make_valid_effect()],
        "effect_die": None,
        "prerequisite": None,
    }


def make_valid_combat_skill() -> dict[str, Any]:
    return {
        "id": "skill-1",
        "name": "Fireball",
        "description": "A ball of fire",
        "tags": ["magic", "fire"],
        "acquisition_source_ids": ["src-1"],
        "levels": [make_valid_level(i) for i in range(1, 6)],
        "allowed_actor_types": ["player"],
    }


def test_combat_skill_levels_validation() -> None:
    data = make_valid_combat_skill()

    # Missing level
    data["levels"] = data["levels"][:4]
    with pytest.raises(ValidationError) as exc:
        CombatSkill(**data)
    assert "exactly 5 levels" in str(exc.value)

    # Duplicate level
    data["levels"] = [
        make_valid_level(1),
        make_valid_level(1),
        make_valid_level(3),
        make_valid_level(4),
        make_valid_level(5),
    ]
    with pytest.raises(ValidationError) as exc:
        CombatSkill(**data)
    assert "out of order or invalid" in str(exc.value)


def test_combat_skill_bad_mana() -> None:
    data = make_valid_combat_skill()
    data["levels"][0]["mana_cost"] = -1
    with pytest.raises(ValidationError):
        CombatSkill(**data)

    data["levels"][0]["mana_cost"] = 11
    with pytest.raises(ValidationError):
        CombatSkill(**data)


def test_arbitrary_effect_kind() -> None:
    data = make_valid_effect()
    data["kind"] = "magic_power"
    with pytest.raises(ValidationError):
        EffectDefinition(**data)


def test_malformed_effect_table() -> None:
    with pytest.raises(ValidationError):
        EffectDieTable(
            **{
                "natural_1": [],
                "low": [],
                "standard": [],
                "strong": [],
                # missing natural_20
            }
        )


def test_skill_tree_graph_validation() -> None:
    data = {
        "id": "tree-1",
        "nodes": [
            {"id": "node-1", "skill_id": "skill-1", "cost": 1},
            {"id": "node-2", "skill_id": "skill-2", "cost": 1},
        ],
        "edges": [{"source_node_id": "node-1", "target_node_id": "node-2"}],
    }

    # Valid
    SkillTree(**data)  # type: ignore

    # Self-reference
    bad_data = data.copy()
    bad_data["edges"] = [{"source_node_id": "node-1", "target_node_id": "node-1"}]
    with pytest.raises(ValidationError) as exc:
        SkillTree(**bad_data)  # type: ignore
    assert "cannot self-reference" in str(exc.value)

    # Unknown edge
    bad_data["edges"] = [{"source_node_id": "node-1", "target_node_id": "node-3"}]
    with pytest.raises(ValidationError) as exc:
        SkillTree(**bad_data)  # type: ignore
    assert "target node not in tree" in str(exc.value)


def test_fusion_recipe_validation() -> None:
    data = {
        "id": "recipe-1",
        "source_skill_ids": ["skill-1", "skill-2"],
        "result_skill_id": "skill-3",
        "catalyst_item_id": "item-1",
        "catalyst_quantity": 1,
        "unlock_conditions": [],
        "location_or_specialist_ids": [],
        "companion_backup_skill_id": "skill-4",
        "power_budget": 100,
    }

    # Valid
    FusionRecipe(**data)  # type: ignore

    # Unsorted sources
    bad_data = data.copy()
    bad_data["source_skill_ids"] = ["skill-2", "skill-1"]
    with pytest.raises(ValidationError) as exc:
        FusionRecipe(**bad_data)  # type: ignore
    assert "strictly sorted" in str(exc.value)

    # Result conflict
    bad_data["source_skill_ids"] = ["skill-1", "skill-2"]
    bad_data["result_skill_id"] = "skill-1"
    with pytest.raises(ValidationError) as exc:
        FusionRecipe(**bad_data)  # type: ignore
    assert "result skill cannot equal" in str(exc.value)


def test_point_buy_table() -> None:
    data = {
        "budget": 27,
        "minimum": 8,
        "maximum_before_bonus": 15,
        "maximum_after_bonus": 17,
        "cost_map": {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9},
    }

    PointBuyDefinition(**data)  # type: ignore

    # Wrong table
    bad_data = data.copy()
    bad_data["cost_map"] = {8: 0, 9: 1}
    with pytest.raises(ValidationError) as exc:
        PointBuyDefinition(**bad_data)  # type: ignore
    assert "does not match the standard progression rules" in str(exc.value)
