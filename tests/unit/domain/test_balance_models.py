"""Tests for balance models."""

from typing import Any

import pytest
from pydantic import ValidationError

from domain.models.balance import BalanceFile, DifficultyProfiles


def make_valid_profiles() -> dict[str, Any]:
    return {
        "story": {
            "dc_adjustment": -2,
            "enemy_hp_ratio": {"numerator": 7, "denominator": 10},
            "enemy_damage_ratio": {"numerator": 1, "denominator": 2},
            "enemy_armour_ratio": {"numerator": 1, "denominator": 1},
            "luck_capacity": 3,
        },
        "normal": {
            "dc_adjustment": 0,
            "enemy_hp_ratio": {"numerator": 1, "denominator": 1},
            "enemy_damage_ratio": {"numerator": 1, "denominator": 1},
            "enemy_armour_ratio": {"numerator": 1, "denominator": 1},
            "luck_capacity": 2,
        },
        "hard": {
            "dc_adjustment": 2,
            "enemy_hp_ratio": {"numerator": 5, "denominator": 4},
            "enemy_damage_ratio": {"numerator": 3, "denominator": 2},
            "enemy_armour_ratio": {"numerator": 1, "denominator": 1},
            "luck_capacity": 1,
        },
    }


def make_valid_balance() -> dict[str, Any]:
    return {
        "campaign_id": "test",
        "campaign_version": "1.0.0",
        "difficulty_profiles": make_valid_profiles(),
        "level_xp_thresholds": {1: 0, 2: 100, 3: 300},
        "dc_bands": {
            "easy": 8,
            "standard": 12,
            "difficult": 15,
            "expert": 18,
            "exceptional": 22,
            "near_impossible": 25,
        },
        "modifier_limits": {},
        "effect_limits": {},
        "enemy_power_formula": {},
        "encounter_targets": {},
        "fusion_limits": {},
        "boss_allowances": {},
    }


def test_difficulty_profiles_exact_match() -> None:
    data = make_valid_profiles()

    # Valid
    DifficultyProfiles(**data)

    # Invalid story dc
    data["story"]["dc_adjustment"] = 0
    with pytest.raises(ValidationError) as exc:
        DifficultyProfiles(**data)
    assert "Story DC adjustment must be -2" in str(exc.value)


def test_level_xp_thresholds() -> None:
    data = make_valid_balance()

    # Valid
    BalanceFile(**data)

    # Missing level 1
    bad_data = data.copy()
    bad_data["level_xp_thresholds"] = {2: 100}
    with pytest.raises(ValidationError) as exc:
        BalanceFile(**bad_data)
    assert "must start at level 1" in str(exc.value)

    # Level 1 not 0 XP
    bad_data["level_xp_thresholds"] = {1: 10, 2: 100}
    with pytest.raises(ValidationError) as exc:
        BalanceFile(**bad_data)
    assert "must start at level 1 with 0 XP" in str(exc.value)

    # Non-contiguous
    bad_data["level_xp_thresholds"] = {1: 0, 3: 300}
    with pytest.raises(ValidationError) as exc:
        BalanceFile(**bad_data)
    assert "must be contiguous" in str(exc.value)

    # Not strictly increasing
    bad_data["level_xp_thresholds"] = {1: 0, 2: 100, 3: 100}
    with pytest.raises(ValidationError) as exc:
        BalanceFile(**bad_data)
    assert "strictly increase" in str(exc.value)
