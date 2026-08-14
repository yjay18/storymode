"""Point buy validation and background application rules."""

from dataclasses import dataclass

from domain.models.character import BackgroundDefinition, StatBlock, StatName
from domain.models.skill import PointBuyDefinition


@dataclass(frozen=True)
class PointBuyResult:
    """Result of a point buy validation."""

    total_cost: int | None
    errors: list[str]

    @property
    def is_valid(self) -> bool:
        return not self.errors and self.total_cost is not None


def validate_point_buy(
    stats: dict[StatName, int], definition: PointBuyDefinition
) -> PointBuyResult:
    """Validate a set of stats against a point buy definition.

    Returns the total cost and an empty list of errors if valid,
    or None and a list of specific string errors if invalid.
    """
    errors: list[str] = []

    # Check for missing or extra stats
    expected_stats = set(StatName)
    provided_stats = set(stats.keys())

    missing = expected_stats - provided_stats
    if missing:
        errors.append(f"Missing stats: {', '.join(sorted(s.value for s in missing))}")

    extra = provided_stats - expected_stats
    if extra:
        errors.append(f"Extra stats provided: {', '.join(sorted(str(s) for s in extra))}")

    if errors:
        return PointBuyResult(total_cost=None, errors=errors)

    total_cost = 0

    for stat_name in StatName:
        score = stats[stat_name]

        if score < definition.minimum:
            errors.append(f"{stat_name.value} score {score} is below minimum {definition.minimum}")
            continue

        if score > definition.maximum_before_bonus:
            errors.append(
                f"{stat_name.value} score {score} is above pre-bonus maximum "
                f"{definition.maximum_before_bonus}"
            )
            continue

        cost = definition.cost_map.get(score)
        if cost is None:
            errors.append(f"No cost defined for score {score}")
            continue

        total_cost += cost

    if not errors and total_cost != definition.budget:
        errors.append(f"Total cost {total_cost} does not equal exactly {definition.budget}")

    if errors:
        return PointBuyResult(total_cost=None, errors=errors)

    return PointBuyResult(total_cost=total_cost, errors=[])


@dataclass(frozen=True)
class BackgroundApplyResult:
    """Result of applying a background bonus."""

    stats: StatBlock | None
    errors: list[str]

    @property
    def is_valid(self) -> bool:
        return not self.errors and self.stats is not None


def apply_background_bonus(
    stats: dict[StatName, int], background: BackgroundDefinition, definition: PointBuyDefinition
) -> BackgroundApplyResult:
    """Apply a background bonus to a set of stats.

    Validates that the resulting score does not exceed the maximum allowed after bonus.
    The stats dictionary is not mutated.
    """
    # Verify we have all stats
    if set(stats.keys()) != set(StatName):
        return BackgroundApplyResult(
            stats=None, errors=["Input stats must contain exactly the six core statistics"]
        )

    result_dict = dict(stats)
    bonus_stat = background.stat_bonus

    result_dict[bonus_stat] += background.stat_bonus_value

    new_score = result_dict[bonus_stat]
    if new_score > definition.maximum_after_bonus:
        return BackgroundApplyResult(
            stats=None,
            errors=[
                f"Applying background bonus to {bonus_stat.value} results in "
                f"score {new_score}, which exceeds maximum {definition.maximum_after_bonus}"
            ],
        )

    try:
        stat_block = StatBlock(**result_dict)
    except ValueError as e:
        return BackgroundApplyResult(stats=None, errors=[f"Validation error: {e}"])

    return BackgroundApplyResult(stats=stat_block, errors=[])
