"""Balance campaign models."""

from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from domain.models.common import EntityId, FrozenModel, Rational, SemanticVersion


class DifficultyProfile(FrozenModel):
    """Exact difficulty multipliers."""

    dc_adjustment: int
    enemy_hp_ratio: Rational
    enemy_damage_ratio: Rational
    enemy_armour_ratio: Rational
    luck_capacity: int


class DifficultyProfiles(FrozenModel):
    """The three required difficulty profiles."""

    story: DifficultyProfile
    normal: DifficultyProfile
    hard: DifficultyProfile

    @model_validator(mode="after")
    def check_exact_rules(self) -> "DifficultyProfiles":
        """Profiles must exactly match difficulty-rules.md."""
        # Story
        if self.story.dc_adjustment != -2:
            raise ValueError("Story DC adjustment must be -2")
        if self.story.enemy_hp_ratio.numerator != 7 or self.story.enemy_hp_ratio.denominator != 10:
            raise ValueError("Story HP ratio must be 7/10")
        if (
            self.story.enemy_damage_ratio.numerator != 1
            or self.story.enemy_damage_ratio.denominator != 2
        ):
            raise ValueError("Story damage ratio must be 1/2")
        if (
            self.story.enemy_armour_ratio.numerator != 1
            or self.story.enemy_armour_ratio.denominator != 1
        ):
            raise ValueError("Story armour ratio must be unchanged (1/1)")
        if self.story.luck_capacity != 3:
            raise ValueError("Story luck capacity must be 3")

        # Normal
        if self.normal.dc_adjustment != 0:
            raise ValueError("Normal DC adjustment must be 0")
        if self.normal.enemy_hp_ratio.numerator != 1 or self.normal.enemy_hp_ratio.denominator != 1:
            raise ValueError("Normal HP ratio must be 1/1")
        if (
            self.normal.enemy_damage_ratio.numerator != 1
            or self.normal.enemy_damage_ratio.denominator != 1
        ):
            raise ValueError("Normal damage ratio must be 1/1")
        if (
            self.normal.enemy_armour_ratio.numerator != 1
            or self.normal.enemy_armour_ratio.denominator != 1
        ):
            raise ValueError("Normal armour ratio must be unchanged (1/1)")
        if self.normal.luck_capacity != 2:
            raise ValueError("Normal luck capacity must be 2")

        # Hard
        if self.hard.dc_adjustment != 2:
            raise ValueError("Hard DC adjustment must be 2")
        if self.hard.enemy_hp_ratio.numerator != 5 or self.hard.enemy_hp_ratio.denominator != 4:
            raise ValueError("Hard HP ratio must be 5/4")
        if (
            self.hard.enemy_damage_ratio.numerator != 3
            or self.hard.enemy_damage_ratio.denominator != 2
        ):
            raise ValueError("Hard damage ratio must be 3/2")
        if (
            self.hard.enemy_armour_ratio.numerator != 1
            or self.hard.enemy_armour_ratio.denominator != 1
        ):
            raise ValueError("Hard armour ratio must be unchanged (1/1)")
        if self.hard.luck_capacity != 1:
            raise ValueError("Hard luck capacity must be 1")

        return self


class DcBands(FrozenModel):
    """The expected DC bands."""

    easy: Literal[8] = 8
    standard: Literal[12] = 12
    difficult: Literal[15] = 15
    expert: Literal[18] = 18
    exceptional: Literal[22] = 22
    near_impossible: Annotated[int, Field(ge=25)]


class BalanceFile(FrozenModel):
    """The root balance file structure."""

    schema_version: Literal[1] = 1
    campaign_id: EntityId
    campaign_version: SemanticVersion
    difficulty_profiles: DifficultyProfiles
    level_xp_thresholds: dict[int, int]
    dc_bands: DcBands
    modifier_limits: dict[str, Any]
    effect_limits: dict[str, Any]
    enemy_power_formula: dict[str, Any]
    encounter_targets: dict[str, Any]
    fusion_limits: dict[str, Any]
    boss_allowances: dict[str, Any]

    @model_validator(mode="after")
    def check_level_xp(self) -> "BalanceFile":
        """XP thresholds must start at level 1 with 0 XP and strictly increase."""
        if 1 not in self.level_xp_thresholds or self.level_xp_thresholds[1] != 0:
            raise ValueError("Level XP must start at level 1 with 0 XP")

        levels = sorted(self.level_xp_thresholds.keys())
        for i in range(1, len(levels)):
            prev_lvl = levels[i - 1]
            curr_lvl = levels[i]
            if curr_lvl != prev_lvl + 1:
                raise ValueError("Level thresholds must be contiguous")
            if self.level_xp_thresholds[curr_lvl] <= self.level_xp_thresholds[prev_lvl]:
                raise ValueError("XP thresholds must strictly increase")

        return self
