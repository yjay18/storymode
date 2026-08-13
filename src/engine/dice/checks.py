"""Exploration checks and difficulty bands."""

from enum import Enum


class ExplorationBand(str, Enum):
    """Possible outcomes of an exploration check."""
    
    CRITICAL_SUCCESS = "critical_success"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    CRITICAL_FAILURE = "critical_failure"


def calculate_exploration_band(roll: int, total: int, dc: int) -> ExplorationBand:
    """Calculate the outcome band for an exploration check.
    
    1. Natural 20 -> critical success.
    2. Natural 1 -> critical failure.
    3. Total at least DC -> success.
    4. Total from DC-3 through DC-1 -> near miss/partial success.
    5. Lower total -> failure.
    """
    if roll == 20:
        return ExplorationBand.CRITICAL_SUCCESS
    if roll == 1:
        return ExplorationBand.CRITICAL_FAILURE
    if total >= dc:
        return ExplorationBand.SUCCESS
    if dc - 3 <= total <= dc - 1:
        return ExplorationBand.PARTIAL_SUCCESS
    return ExplorationBand.FAILURE


def sum_modifiers(named_modifiers: dict[str, int]) -> int:
    """Sum the given named modifiers."""
    return sum(named_modifiers.values())
