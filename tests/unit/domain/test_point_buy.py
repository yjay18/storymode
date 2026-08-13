"""Tests for point buy validation."""

import pytest

from domain.models.character import BackgroundDefinition, StatName
from domain.models.skill import PointBuyDefinition
from domain.rules.point_buy import apply_background_bonus, validate_point_buy


@pytest.fixture
def point_buy_def() -> PointBuyDefinition:
    return PointBuyDefinition(
        cost_map={8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
    )


@pytest.fixture
def background() -> BackgroundDefinition:
    return BackgroundDefinition(
        id="bg-1",
        name="Test",
        description="x",
        stat_bonus=StatName.STRENGTH,
        stat_bonus_value=2,
        starting_skill_ids=[],
        starting_item_ids=[],
        starting_fact_ids=[],
    )


def test_validate_point_buy_valid(point_buy_def: PointBuyDefinition) -> None:
    # Example valid 27 point buy: 15 (9), 14 (7), 13 (5), 12 (4), 10 (2), 8 (0)
    stats = {
        StatName.STRENGTH: 15,
        StatName.DEXTERITY: 14,
        StatName.CONSTITUTION: 13,
        StatName.INTELLIGENCE: 12,
        StatName.WISDOM: 10,
        StatName.CHARISMA: 8,
    }
    
    result = validate_point_buy(stats, point_buy_def)
    assert result.is_valid
    assert result.total_cost == 27
    assert not result.errors


def test_validate_point_buy_invalid_total(point_buy_def: PointBuyDefinition) -> None:
    # 26 points
    stats = {
        StatName.STRENGTH: 15,
        StatName.DEXTERITY: 14,
        StatName.CONSTITUTION: 13,
        StatName.INTELLIGENCE: 12,
        StatName.WISDOM: 9, # 9 costs 1, so total is 26
        StatName.CHARISMA: 8,
    }
    result = validate_point_buy(stats, point_buy_def)
    assert not result.is_valid
    assert result.total_cost is None
    assert "exactly 27" in result.errors[0]

    # 28 points
    stats[StatName.WISDOM] = 11 # 11 costs 3, so total is 28
    result = validate_point_buy(stats, point_buy_def)
    assert not result.is_valid
    assert "exactly 27" in result.errors[0]


def test_validate_point_buy_boundary_scores(point_buy_def: PointBuyDefinition) -> None:
    # Out of bounds high
    stats = {
        StatName.STRENGTH: 16, # Invalid, > 15
        StatName.DEXTERITY: 14,
        StatName.CONSTITUTION: 12,
        StatName.INTELLIGENCE: 10,
        StatName.WISDOM: 10,
        StatName.CHARISMA: 8,
    }
    result = validate_point_buy(stats, point_buy_def)
    assert not result.is_valid
    assert any("above pre-bonus maximum" in err for err in result.errors)

    # Out of bounds low
    stats[StatName.STRENGTH] = 7
    result = validate_point_buy(stats, point_buy_def)
    assert not result.is_valid
    assert any("below minimum" in err for err in result.errors)


def test_validate_point_buy_malformed_stats(point_buy_def: PointBuyDefinition) -> None:
    # Missing stat
    stats = {
        StatName.STRENGTH: 15,
        StatName.DEXTERITY: 14,
        StatName.CONSTITUTION: 13,
        StatName.INTELLIGENCE: 12,
        StatName.WISDOM: 10,
    }
    result = validate_point_buy(stats, point_buy_def) # type: ignore
    assert not result.is_valid
    assert any("Missing stats" in err for err in result.errors)

    # Extra stat
    stats[StatName.CHARISMA] = 8
    stats["luck"] = 10 # type: ignore
    result = validate_point_buy(stats, point_buy_def)
    assert not result.is_valid
    assert any("Extra stats" in err for err in result.errors)


def test_apply_background_bonus_valid(
    point_buy_def: PointBuyDefinition, background: BackgroundDefinition
) -> None:
    stats = {
        StatName.STRENGTH: 15,
        StatName.DEXTERITY: 14,
        StatName.CONSTITUTION: 13,
        StatName.INTELLIGENCE: 12,
        StatName.WISDOM: 10,
        StatName.CHARISMA: 8,
    }
    
    # Input unchanged
    original_strength = stats[StatName.STRENGTH]
    
    result = apply_background_bonus(stats, background, point_buy_def)
    assert result.is_valid
    assert result.stats is not None
    assert result.stats.strength == 17
    assert stats[StatName.STRENGTH] == original_strength


def test_apply_background_bonus_rejects_18(
    point_buy_def: PointBuyDefinition, background: BackgroundDefinition
) -> None:
    # If a rule or a manual override got strength to 16, +2 makes it 18 > 17
    stats = {
        StatName.STRENGTH: 16,
        StatName.DEXTERITY: 14,
        StatName.CONSTITUTION: 13,
        StatName.INTELLIGENCE: 12,
        StatName.WISDOM: 10,
        StatName.CHARISMA: 8,
    }
    
    result = apply_background_bonus(stats, background, point_buy_def)
    assert not result.is_valid
    assert any("exceeds maximum 17" in err for err in result.errors)
