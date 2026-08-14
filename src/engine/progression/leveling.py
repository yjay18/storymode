"""Progression leveling and XP grant rules (PROG-01)."""

from __future__ import annotations

from domain.models.common import FrozenModel
from domain.models.runtime_state import RuntimeState


class LevelingResult(FrozenModel):
    """Result summary of granting XP to the protagonist."""

    previous_xp: int
    new_xp: int
    previous_level: int
    new_level: int
    levels_gained: int
    tokens_gained: int
    total_tokens: int


def validate_xp_thresholds(level_xp_thresholds: dict[int, int]) -> None:
    """Validate that XP thresholds table is valid and strictly increasing."""
    if not level_xp_thresholds:
        raise ValueError("XP thresholds table cannot be empty")
    if 1 not in level_xp_thresholds or level_xp_thresholds[1] != 0:
        raise ValueError("XP thresholds table must start at level 1 with 0 XP")

    levels = sorted(level_xp_thresholds.keys())
    for i in range(1, len(levels)):
        prev_lvl = levels[i - 1]
        curr_lvl = levels[i]
        if curr_lvl != prev_lvl + 1:
            raise ValueError("Level thresholds must be contiguous")
        if level_xp_thresholds[curr_lvl] <= level_xp_thresholds[prev_lvl]:
            raise ValueError("XP thresholds must strictly increase")


def calculate_level_from_xp(
    xp: int,
    level_xp_thresholds: dict[int, int],
) -> int:
    """Calculate the derived level for a given XP amount against thresholds."""
    validate_xp_thresholds(level_xp_thresholds)
    if xp < 0:
        raise ValueError(f"XP cannot be negative: {xp}")

    current_level = 1
    for level in sorted(level_xp_thresholds.keys()):
        if xp >= level_xp_thresholds[level]:
            current_level = level
        else:
            break
    return current_level


def grant_xp(
    state: RuntimeState,
    xp_amount: int,
    level_xp_thresholds: dict[int, int],
) -> tuple[RuntimeState, LevelingResult]:
    """Grant non-negative XP to the protagonist and apply level/token gains.

    Returns the updated RuntimeState and a LevelingResult summary.
    Raises ValueError if:
    - xp_amount is negative
    - level_xp_thresholds is invalid
    """
    if xp_amount < 0:
        raise ValueError(f"Cannot grant negative XP: {xp_amount}")

    validate_xp_thresholds(level_xp_thresholds)

    prev_xp = state.player.xp
    prev_level = state.player.level
    prev_tokens = state.player.upgrade_tokens

    new_xp = prev_xp + xp_amount
    new_level = calculate_level_from_xp(new_xp, level_xp_thresholds)

    levels_gained = max(0, new_level - prev_level)
    tokens_gained = levels_gained
    new_tokens = prev_tokens + tokens_gained

    new_player = state.player.model_copy(
        update={
            "xp": new_xp,
            "level": new_level,
            "upgrade_tokens": new_tokens,
        }
    )

    new_state = state.model_copy(update={"player": new_player})

    result = LevelingResult(
        previous_xp=prev_xp,
        new_xp=new_xp,
        previous_level=prev_level,
        new_level=new_level,
        levels_gained=levels_gained,
        tokens_gained=tokens_gained,
        total_tokens=new_tokens,
    )

    return new_state, result
