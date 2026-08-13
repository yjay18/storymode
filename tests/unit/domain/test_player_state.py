"""Tests for player state runtime models."""

import pytest

from domain.models.character import StatBlock
from domain.models.player_state import PlayerState
from domain.models.runtime_common import (
    InventoryEntry,
    KnownCombatSkill,
    ResourceValue,
)


@pytest.fixture
def valid_stats() -> StatBlock:
    return StatBlock(
        strength=10,
        dexterity=10,
        intelligence=10,
        charisma=10,
        constitution=10,
        wisdom=10,
    )


def test_resource_value_bounds() -> None:
    # Valid
    rv = ResourceValue(current=5, maximum=10)
    assert rv.current == 5
    assert rv.maximum == 10

    rv_full = ResourceValue(current=10, maximum=10)
    assert rv_full.current == 10

    rv_empty = ResourceValue(current=0, maximum=10)
    assert rv_empty.current == 0

    # Invalid
    with pytest.raises(ValueError, match="cannot exceed maximum"):
        ResourceValue(current=11, maximum=10)

    with pytest.raises(ValueError):
        ResourceValue(current=-1, maximum=10)


def test_player_state_minimal_valid(valid_stats: StatBlock) -> None:
    player = PlayerState(
        id="player-1",
        name="Hero",
        background_id="bg-1",
        stats=valid_stats,
        hp=ResourceValue(current=10, maximum=10),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=10, maximum=10),
        mana_regen=2,
        speed=30,
        luck_current=1,
        luck_capacity=3,
    )
    assert player.id == "player-1"
    assert player.level == 1
    assert player.xp == 0
    assert player.upgrade_tokens == 0


def test_player_state_luck_bounds(valid_stats: StatBlock) -> None:
    with pytest.raises(ValueError, match="cannot exceed luck_capacity"):
        PlayerState(
            id="player-1",
            name="Hero",
            background_id="bg-1",
            stats=valid_stats,
            hp=ResourceValue(current=10, maximum=10),
            armour=ResourceValue(current=0, maximum=5),
            mana=ResourceValue(current=10, maximum=10),
            mana_regen=2,
            speed=30,
            luck_current=4,
            luck_capacity=3,
        )


def test_player_state_non_combat_skill_bounds(valid_stats: StatBlock) -> None:
    with pytest.raises(ValueError, match="between 0 and 5"):
        PlayerState(
            id="player-1",
            name="Hero",
            background_id="bg-1",
            stats=valid_stats,
            hp=ResourceValue(current=10, maximum=10),
            armour=ResourceValue(current=0, maximum=5),
            mana=ResourceValue(current=10, maximum=10),
            mana_regen=2,
            speed=30,
            luck_capacity=3,
            non_combat_skill_ranks={"skill-1": 6},
        )


def test_player_state_known_combat_skills_unique(valid_stats: StatBlock) -> None:
    with pytest.raises(ValueError, match="duplicate skill_ids"):
        PlayerState(
            id="player-1",
            name="Hero",
            background_id="bg-1",
            stats=valid_stats,
            hp=ResourceValue(current=10, maximum=10),
            armour=ResourceValue(current=0, maximum=5),
            mana=ResourceValue(current=10, maximum=10),
            mana_regen=2,
            speed=30,
            luck_capacity=3,
            known_combat_skills=[
                KnownCombatSkill(skill_id="slash", level=1, acquisition_source_id="src"),
                KnownCombatSkill(skill_id="slash", level=2, acquisition_source_id="src2"),
            ],
        )


def test_player_state_loadout_invariants(valid_stats: StatBlock) -> None:
    # Unknown skill
    with pytest.raises(ValueError, match="unknown skill_id unknown-skill"):
        PlayerState(
            id="player-1",
            name="Hero",
            background_id="bg-1",
            stats=valid_stats,
            hp=ResourceValue(current=10, maximum=10),
            armour=ResourceValue(current=0, maximum=5),
            mana=ResourceValue(current=10, maximum=10),
            mana_regen=2,
            speed=30,
            luck_capacity=3,
            combat_loadout=["unknown-skill"],
        )

    # Max 4 items
    with pytest.raises(ValueError, match="cannot exceed 4 items"):
        PlayerState(
            id="player-1",
            name="Hero",
            background_id="bg-1",
            stats=valid_stats,
            hp=ResourceValue(current=10, maximum=10),
            armour=ResourceValue(current=0, maximum=5),
            mana=ResourceValue(current=10, maximum=10),
            mana_regen=2,
            speed=30,
            luck_capacity=3,
            known_combat_skills=[
                KnownCombatSkill(skill_id=f"skill-{i}", level=1, acquisition_source_id="src")
                for i in range(5)
            ],
            combat_loadout=[f"skill-{i}" for i in range(5)],
        )

    # Duplicate items
    with pytest.raises(ValueError, match="duplicate skill_ids"):
        PlayerState(
            id="player-1",
            name="Hero",
            background_id="bg-1",
            stats=valid_stats,
            hp=ResourceValue(current=10, maximum=10),
            armour=ResourceValue(current=0, maximum=5),
            mana=ResourceValue(current=10, maximum=10),
            mana_regen=2,
            speed=30,
            luck_capacity=3,
            known_combat_skills=[
                KnownCombatSkill(skill_id="slash", level=1, acquisition_source_id="src"),
            ],
            combat_loadout=["slash", "slash"],
        )


def test_player_state_inventory_equipment(valid_stats: StatBlock) -> None:
    # Duplicate item ids in inventory
    with pytest.raises(ValueError, match="duplicate item_ids"):
        PlayerState(
            id="player-1",
            name="Hero",
            background_id="bg-1",
            stats=valid_stats,
            hp=ResourceValue(current=10, maximum=10),
            armour=ResourceValue(current=0, maximum=5),
            mana=ResourceValue(current=10, maximum=10),
            mana_regen=2,
            speed=30,
            luck_capacity=3,
            inventory=[
                InventoryEntry(item_id="potion", quantity=1),
                InventoryEntry(item_id="potion", quantity=2),
            ],
        )

    # Equipment not in inventory
    with pytest.raises(ValueError, match="equipped item_id sword is not in inventory"):
        PlayerState(
            id="player-1",
            name="Hero",
            background_id="bg-1",
            stats=valid_stats,
            hp=ResourceValue(current=10, maximum=10),
            armour=ResourceValue(current=0, maximum=5),
            mana=ResourceValue(current=10, maximum=10),
            mana_regen=2,
            speed=30,
            luck_capacity=3,
            equipment=[
                InventoryEntry(item_id="sword", quantity=1),
            ],
        )

    # Equipment quantity exceeds inventory
    with pytest.raises(ValueError, match="equipped quantity of sword exceeds inventory"):
        PlayerState(
            id="player-1",
            name="Hero",
            background_id="bg-1",
            stats=valid_stats,
            hp=ResourceValue(current=10, maximum=10),
            armour=ResourceValue(current=0, maximum=5),
            mana=ResourceValue(current=10, maximum=10),
            mana_regen=2,
            speed=30,
            luck_capacity=3,
            inventory=[
                InventoryEntry(item_id="sword", quantity=1),
            ],
            equipment=[
                InventoryEntry(item_id="sword", quantity=2),
            ],
        )

    # Valid inventory and equipment
    player = PlayerState(
        id="player-1",
        name="Hero",
        background_id="bg-1",
        stats=valid_stats,
        hp=ResourceValue(current=10, maximum=10),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=10, maximum=10),
        mana_regen=2,
        speed=30,
        luck_capacity=3,
        inventory=[
            InventoryEntry(item_id="sword", quantity=2),
        ],
        equipment=[
            InventoryEntry(item_id="sword", quantity=1),
        ],
    )
    assert len(player.equipment) == 1
    assert player.equipment[0].item_id == "sword"
