"""Unit tests for rational arithmetic, difficulty scaling, and damage routing."""

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.runtime_common import ResourceValue
from domain.rules.arithmetic import round_rational_half_up, scale_rational
from domain.rules.combat_resources import apply_damage, apply_healing, apply_mana_delta
from domain.rules.difficulty import (
    get_difficulty_dc_adjustment,
    get_difficulty_luck_capacity,
    scale_enemy_damage,
    scale_enemy_hp,
)


def test_round_rational_half_up_edges() -> None:
    # 0/10 -> 0
    assert round_rational_half_up(0, 10) == 0
    # 1/10 (0.1) -> 0
    assert round_rational_half_up(1, 10) == 0
    # 4/10 (0.4) -> 0
    assert round_rational_half_up(4, 10) == 0
    # 5/10 (0.5 ties upward) -> 1
    assert round_rational_half_up(5, 10) == 1
    # 6/10 (0.6) -> 1
    assert round_rational_half_up(6, 10) == 1
    # 14/10 (1.4) -> 1
    assert round_rational_half_up(14, 10) == 1
    # 15/10 (1.5 ties upward) -> 2
    assert round_rational_half_up(15, 10) == 2
    # 25/10 (2.5 ties upward) -> 3
    assert round_rational_half_up(25, 10) == 3


def test_scale_rational_standard_ratios() -> None:
    # 7/10 ratio (Story HP)
    assert scale_rational(0, 7, 10) == 0
    assert scale_rational(1, 7, 10) == 1  # 7/10 = 0.7 -> 1
    assert scale_rational(2, 7, 10) == 1  # 14/10 = 1.4 -> 1
    assert scale_rational(5, 7, 10) == 4  # 35/10 = 3.5 -> 4
    assert scale_rational(10, 7, 10) == 7  # 70/10 = 7.0 -> 7

    # 1/2 ratio (Story Damage)
    assert scale_rational(0, 1, 2) == 0
    assert scale_rational(1, 1, 2) == 1  # 1/2 = 0.5 -> 1
    assert scale_rational(2, 1, 2) == 1  # 2/2 = 1.0 -> 1
    assert scale_rational(3, 1, 2) == 2  # 3/2 = 1.5 -> 2
    assert scale_rational(4, 1, 2) == 2  # 4/2 = 2.0 -> 2

    # 5/4 ratio (Hard HP)
    assert scale_rational(0, 5, 4) == 0
    assert scale_rational(1, 5, 4) == 1  # 5/4 = 1.25 -> 1
    assert scale_rational(2, 5, 4) == 3  # 10/4 = 2.5 -> 3
    assert scale_rational(3, 5, 4) == 4  # 15/4 = 3.75 -> 4
    assert scale_rational(4, 5, 4) == 5  # 20/4 = 5.0 -> 5

    # 3/2 ratio (Hard Damage)
    assert scale_rational(0, 3, 2) == 0
    assert scale_rational(1, 3, 2) == 2  # 3/2 = 1.5 -> 2
    assert scale_rational(2, 3, 2) == 3  # 6/2 = 3.0 -> 3
    assert scale_rational(3, 3, 2) == 5  # 9/2 = 4.5 -> 5


def test_arithmetic_input_validation() -> None:
    # Denominator <= 0
    with pytest.raises(ValueError, match="Denominator must be positive"):
        round_rational_half_up(5, 0)
    with pytest.raises(ValueError, match="Denominator must be positive"):
        round_rational_half_up(5, -1)
    with pytest.raises(ValueError, match="Denominator must be positive"):
        scale_rational(5, 1, -2)

    # Negative numerator or value
    with pytest.raises(ValueError, match="Numerator must be non-negative"):
        round_rational_half_up(-1, 2)
    with pytest.raises(ValueError, match="Value must be non-negative"):
        scale_rational(-5, 1, 2)
    with pytest.raises(ValueError, match="Numerator must be non-negative"):
        scale_rational(5, -1, 2)

    # Booleans explicitly rejected
    bool_val: object = True
    bool_false: object = False
    with pytest.raises(TypeError, match="Boolean values are not allowed"):
        round_rational_half_up(bool_val, 2)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Boolean values are not allowed"):
        round_rational_half_up(2, bool_false)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Boolean values are not allowed"):
        scale_rational(bool_val, 1, 2)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Boolean values are not allowed"):
        scale_rational(5, bool_val, 2)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Boolean values are not allowed"):
        scale_rational(5, 1, bool_false)  # type: ignore[arg-type]


def test_difficulty_scaling_enemy_hp() -> None:
    # Zero HP stays 0
    assert scale_enemy_hp(0, DefaultDifficulty.STORY) == 0
    assert scale_enemy_hp(0, DefaultDifficulty.NORMAL) == 0
    assert scale_enemy_hp(0, DefaultDifficulty.HARD) == 0

    # Minimum positive HP is always >= 1
    assert scale_enemy_hp(1, DefaultDifficulty.STORY) == 1
    assert scale_enemy_hp(1, DefaultDifficulty.NORMAL) == 1
    assert scale_enemy_hp(1, DefaultDifficulty.HARD) == 1

    # Base HP 10
    assert scale_enemy_hp(10, DefaultDifficulty.STORY) == 7
    assert scale_enemy_hp(10, DefaultDifficulty.NORMAL) == 10
    assert scale_enemy_hp(10, DefaultDifficulty.HARD) == 13  # 50/4 = 12.5 -> 13

    # Base HP 20
    assert scale_enemy_hp(20, DefaultDifficulty.STORY) == 14
    assert scale_enemy_hp(20, DefaultDifficulty.NORMAL) == 20
    assert scale_enemy_hp(20, DefaultDifficulty.HARD) == 25


def test_difficulty_scaling_enemy_damage() -> None:
    assert scale_enemy_damage(0, DefaultDifficulty.STORY) == 0
    assert scale_enemy_damage(0, DefaultDifficulty.NORMAL) == 0
    assert scale_enemy_damage(0, DefaultDifficulty.HARD) == 0

    assert scale_enemy_damage(6, DefaultDifficulty.STORY) == 3
    assert scale_enemy_damage(6, DefaultDifficulty.NORMAL) == 6
    assert scale_enemy_damage(6, DefaultDifficulty.HARD) == 9

    assert scale_enemy_damage(5, DefaultDifficulty.STORY) == 3  # 5/2 = 2.5 -> 3
    assert scale_enemy_damage(5, DefaultDifficulty.HARD) == 8  # 15/2 = 7.5 -> 8


def test_difficulty_dc_and_luck() -> None:
    assert get_difficulty_dc_adjustment(DefaultDifficulty.STORY) == -2
    assert get_difficulty_dc_adjustment(DefaultDifficulty.NORMAL) == 0
    assert get_difficulty_dc_adjustment(DefaultDifficulty.HARD) == 2

    assert get_difficulty_luck_capacity(DefaultDifficulty.STORY) == 3
    assert get_difficulty_luck_capacity(DefaultDifficulty.NORMAL) == 2
    assert get_difficulty_luck_capacity(DefaultDifficulty.HARD) == 1


def test_apply_damage_scenarios() -> None:
    # 1. Armour-only absorption
    hp = ResourceValue(current=10, maximum=10)
    armour = ResourceValue(current=5, maximum=5)
    new_hp, new_armour, res = apply_damage(hp, armour, 3)

    assert new_armour.current == 2
    assert new_hp.current == 10
    assert res.damage == 3
    assert res.armour_absorbed == 3
    assert res.armour_after == 2
    assert res.hp_damage == 0
    assert res.hp_after == 10
    assert not res.is_defeated

    # 2. Exact armour breakage
    new_hp, new_armour, res = apply_damage(hp, armour, 5)
    assert new_armour.current == 0
    assert new_hp.current == 10
    assert res.armour_absorbed == 5
    assert res.hp_damage == 0
    assert not res.is_defeated

    # 3. Armour spill into HP
    new_hp, new_armour, res = apply_damage(hp, armour, 8)
    assert new_armour.current == 0
    assert new_hp.current == 7
    assert res.armour_absorbed == 5
    assert res.hp_damage == 3
    assert res.hp_after == 7
    assert not res.is_defeated

    # 4. No armour direct HP damage
    armour_zero = ResourceValue(current=0, maximum=5)
    new_hp, new_armour, res = apply_damage(hp, armour_zero, 4)
    assert new_armour.current == 0
    assert new_hp.current == 6
    assert res.armour_absorbed == 0
    assert res.hp_damage == 4
    assert res.hp_after == 6
    assert not res.is_defeated

    # 5. Overkill clamped at 0 HP
    new_hp, new_armour, res = apply_damage(hp, armour_zero, 15)
    assert new_armour.current == 0
    assert new_hp.current == 0
    assert res.armour_absorbed == 0
    assert res.hp_damage == 10  # took all 10 HP
    assert res.hp_after == 0
    assert res.is_defeated


def test_apply_damage_validation() -> None:
    hp = ResourceValue(current=10, maximum=10)
    armour = ResourceValue(current=5, maximum=5)
    bool_val: object = True

    with pytest.raises(ValueError, match="Damage must be non-negative"):
        apply_damage(hp, armour, -1)

    with pytest.raises(TypeError, match="Boolean value not allowed"):
        apply_damage(hp, armour, bool_val)  # type: ignore[arg-type]


def test_apply_healing() -> None:
    hp = ResourceValue(current=5, maximum=10)
    bool_val: object = True

    # Normal partial heal
    new_hp, healed = apply_healing(hp, 3)
    assert new_hp.current == 8
    assert healed == 3

    # Heal capped at max
    new_hp, healed = apply_healing(hp, 10)
    assert new_hp.current == 10
    assert healed == 5

    # Negative heal raises ValueError
    with pytest.raises(ValueError, match="Healing amount must be non-negative"):
        apply_healing(hp, -2)

    # Boolean raises TypeError
    with pytest.raises(TypeError, match="Boolean value not allowed"):
        apply_healing(hp, bool_val)  # type: ignore[arg-type]


def test_apply_mana_delta() -> None:
    mana = ResourceValue(current=5, maximum=10)
    bool_val: object = True

    # Positive regen within max
    new_mana, delta = apply_mana_delta(mana, 3)
    assert new_mana.current == 8
    assert delta == 3

    # Positive regen clamped at max
    new_mana, delta = apply_mana_delta(mana, 10)
    assert new_mana.current == 10
    assert delta == 5

    # Negative cost affordable
    new_mana, delta = apply_mana_delta(mana, -3)
    assert new_mana.current == 2
    assert delta == -3

    # Negative cost unaffordable
    with pytest.raises(ValueError, match="Insufficient mana"):
        apply_mana_delta(mana, -6)

    # Boolean raises TypeError
    with pytest.raises(TypeError, match="Boolean value not allowed"):
        apply_mana_delta(mana, bool_val)  # type: ignore[arg-type]
