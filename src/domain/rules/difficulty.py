"""Difficulty profile rules and scaling math."""

from __future__ import annotations

from dataclasses import dataclass

from domain.models.campaign_meta import DefaultDifficulty
from domain.rules.arithmetic import scale_rational


@dataclass(frozen=True)
class DifficultyProfile:
    """Mathematical scaling factors and rules for a difficulty setting."""

    dc_adjustment: int
    hp_ratio: tuple[int, int]
    damage_ratio: tuple[int, int]
    luck_capacity: int


DIFFICULTY_PROFILES: dict[DefaultDifficulty, DifficultyProfile] = {
    DefaultDifficulty.STORY: DifficultyProfile(
        dc_adjustment=-2,
        hp_ratio=(7, 10),
        damage_ratio=(1, 2),
        luck_capacity=3,
    ),
    DefaultDifficulty.NORMAL: DifficultyProfile(
        dc_adjustment=0,
        hp_ratio=(1, 1),
        damage_ratio=(1, 1),
        luck_capacity=2,
    ),
    DefaultDifficulty.HARD: DifficultyProfile(
        dc_adjustment=2,
        hp_ratio=(5, 4),
        damage_ratio=(3, 2),
        luck_capacity=1,
    ),
}


def get_difficulty_profile(difficulty: DefaultDifficulty) -> DifficultyProfile:
    """Retrieve the DifficultyProfile for a given difficulty setting."""
    if difficulty not in DIFFICULTY_PROFILES:
        raise ValueError(f"Unknown difficulty: {difficulty}")
    return DIFFICULTY_PROFILES[difficulty]


def scale_enemy_hp(base_hp: int, difficulty: DefaultDifficulty) -> int:
    """Scale base enemy HP according to the difficulty profile.

    Scaled positive HP always has a minimum of 1.
    Raises ValueError if base_hp is negative.
    """
    if isinstance(base_hp, bool):
        raise TypeError("Boolean value not allowed for base_hp")
    if not isinstance(base_hp, int):
        raise TypeError("base_hp must be an integer")
    if base_hp < 0:
        raise ValueError(f"base_hp must be non-negative, got {base_hp}")
    if base_hp == 0:
        return 0

    profile = get_difficulty_profile(difficulty)
    num, denom = profile.hp_ratio
    scaled = scale_rational(base_hp, num, denom)
    return max(1, scaled)


def scale_enemy_damage(base_damage: int, difficulty: DefaultDifficulty) -> int:
    """Scale base enemy damage according to the difficulty profile.

    Raises ValueError if base_damage is negative.
    """
    if isinstance(base_damage, bool):
        raise TypeError("Boolean value not allowed for base_damage")
    if not isinstance(base_damage, int):
        raise TypeError("base_damage must be an integer")
    if base_damage < 0:
        raise ValueError(f"base_damage must be non-negative, got {base_damage}")

    profile = get_difficulty_profile(difficulty)
    num, denom = profile.damage_ratio
    return scale_rational(base_damage, num, denom)


def get_difficulty_dc_adjustment(difficulty: DefaultDifficulty) -> int:
    """Get the DC adjustment for checks under the given difficulty."""
    return get_difficulty_profile(difficulty).dc_adjustment


def get_difficulty_luck_capacity(difficulty: DefaultDifficulty) -> int:
    """Get the default Luck capacity for the given difficulty."""
    return get_difficulty_profile(difficulty).luck_capacity
