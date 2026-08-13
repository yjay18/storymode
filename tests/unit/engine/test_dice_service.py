"""Tests for the dice service and checks."""

import datetime
from collections.abc import Callable

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.common import DisplayString, EntityId
from engine.dice.checks import ExplorationBand, calculate_exploration_band
from engine.dice.effects import CombatEffectBand, calculate_combat_band
from engine.dice.service import DiceService
from engine.dice.testing import ScriptedRandomSource


def test_exploration_bands() -> None:
    # 1. Natural 20 precedence
    assert calculate_exploration_band(20, 20-5, 25) == ExplorationBand.CRITICAL_SUCCESS
    
    # 2. Natural 1 precedence
    assert calculate_exploration_band(1, 1+15, 12) == ExplorationBand.CRITICAL_FAILURE
    
    # 3. Exact DC -> Success
    assert calculate_exploration_band(10, 15, 15) == ExplorationBand.SUCCESS
    
    # 4. DC - 1 -> Partial Success
    assert calculate_exploration_band(10, 14, 15) == ExplorationBand.PARTIAL_SUCCESS
    
    # 5. DC - 3 -> Partial Success
    assert calculate_exploration_band(10, 12, 15) == ExplorationBand.PARTIAL_SUCCESS
    
    # 6. DC - 4 -> Failure
    assert calculate_exploration_band(10, 11, 15) == ExplorationBand.FAILURE


def test_combat_bands() -> None:
    assert calculate_combat_band(20) == CombatEffectBand.NATURAL_20
    assert calculate_combat_band(1) == CombatEffectBand.NATURAL_1
    assert calculate_combat_band(2) == CombatEffectBand.LOW
    assert calculate_combat_band(9) == CombatEffectBand.LOW
    assert calculate_combat_band(10) == CombatEffectBand.STANDARD
    assert calculate_combat_band(14) == CombatEffectBand.STANDARD
    assert calculate_combat_band(15) == CombatEffectBand.STRONG
    assert calculate_combat_band(19) == CombatEffectBand.STRONG
    
    with pytest.raises(ValueError):
        calculate_combat_band(21)


def test_dice_service_exploration(
    fixed_clock: datetime.datetime,
    sequential_id_generator: Callable[[], str],
) -> None:
    rng = ScriptedRandomSource([15])
    service = DiceService(
        rng=rng,
        clock=lambda: fixed_clock,
        id_generator=lambda: EntityId(sequential_id_generator())
    )
    
    modifiers = {DisplayString("stat"): 2, DisplayString("penalty"): -1}
    
    total, record = service.roll_exploration_check(
        transaction_id=EntityId("tx-1"),
        revision=1,
        command_id=EntityId("cmd-1"),
        reason=DisplayString("test roll"),
        dc=15,
        difficulty=DefaultDifficulty.NORMAL,
        named_modifiers=modifiers,
    )
    
    # 15 + 2 - 1 = 16
    assert total == 16
    assert record.total == 16
    assert record.outcome == "success"
    assert record.raw_rolls == [15]
    assert record.dc == 15
    assert record.difficulty == DefaultDifficulty.NORMAL
    assert record.named_modifiers == modifiers
    assert record.roll_id == "test-id-0001"
    
    rng.assert_exhausted()


def test_dice_service_combat_and_tie_break(
    fixed_clock: datetime.datetime,
    sequential_id_generator: Callable[[], str],
) -> None:
    rng = ScriptedRandomSource([10, 20])
    service = DiceService(
        rng=rng,
        clock=lambda: fixed_clock,
        id_generator=lambda: EntityId(sequential_id_generator())
    )
    
    # Combat roll (uses 10)
    total, record = service.roll_combat_effect(
        transaction_id=EntityId("tx-1"),
        revision=1,
        command_id=EntityId("cmd-1"),
        reason=DisplayString("combat effect"),
    )
    assert total == 10
    assert record.outcome == "standard"
    assert record.dc is None
    
    # Tie-break roll (uses 20)
    total_tb, record_tb = service.roll_tie_break(
        transaction_id=EntityId("tx-1"),
        revision=1,
        command_id=EntityId("cmd-1"),
        reason=DisplayString("tie break"),
    )
    assert total_tb == 20
    assert record_tb.outcome is None
    assert record_tb.dc is None
    
    rng.assert_exhausted()
