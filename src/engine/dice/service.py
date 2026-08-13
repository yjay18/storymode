"""Dice rolling service."""

import datetime
from collections.abc import Callable

from domain.models.audit import RollRecord
from domain.models.campaign_meta import DefaultDifficulty
from domain.models.common import DisplayString, EntityId
from engine.dice.checks import calculate_exploration_band
from engine.dice.effects import calculate_combat_band
from engine.dice.ports import RandomSource


class DiceService:
    """Service to execute rolls and construct audit records."""

    def __init__(
        self, 
        rng: RandomSource,
        clock: Callable[[], datetime.datetime],
        id_generator: Callable[[], EntityId],
    ) -> None:
        self._rng = rng
        self._clock = clock
        self._id_generator = id_generator

    def roll_exploration_check(
        self,
        transaction_id: EntityId,
        revision: int,
        command_id: EntityId,
        reason: DisplayString,
        dc: int,
        difficulty: DefaultDifficulty,
        named_modifiers: dict[DisplayString, int],
    ) -> tuple[int, RollRecord]:
        """Roll an exploration check, calculate its band, and create a record."""
        # 1. Roll exactly once
        raw_roll = self._rng.roll(20)
        
        # 2. Compute total
        total_modifiers = sum(named_modifiers.values())
        total = raw_roll + total_modifiers
        
        # 3. Compute outcome band
        band = calculate_exploration_band(raw_roll, total, dc)
        
        # 4. Construct record
        record = RollRecord(
            roll_id=self._id_generator(),
            transaction_id=transaction_id,
            revision=revision,
            recorded_at=self._clock(),
            command_id=command_id,
            reason=reason,
            die_sides=20,
            raw_rolls=[raw_roll],
            selected_roll_index=0,
            named_modifiers=named_modifiers,
            total=total,
            dc=dc,
            difficulty=difficulty,
            outcome=DisplayString(band.value),
            confirmed_effect_ids=[],
            supersedes_roll_id=None,
        )
        return total, record

    def roll_combat_effect(
        self,
        transaction_id: EntityId,
        revision: int,
        command_id: EntityId,
        reason: DisplayString,
    ) -> tuple[int, RollRecord]:
        """Roll a combat effect die and create a record."""
        raw_roll = self._rng.roll(20)
        band = calculate_combat_band(raw_roll)
        
        record = RollRecord(
            roll_id=self._id_generator(),
            transaction_id=transaction_id,
            revision=revision,
            recorded_at=self._clock(),
            command_id=command_id,
            reason=reason,
            die_sides=20,
            raw_rolls=[raw_roll],
            selected_roll_index=0,
            named_modifiers={},
            total=raw_roll,
            dc=None,
            difficulty=None,
            outcome=DisplayString(band.value),
            confirmed_effect_ids=[],
            supersedes_roll_id=None,
        )
        return raw_roll, record

    def roll_tie_break(
        self,
        transaction_id: EntityId,
        revision: int,
        command_id: EntityId,
        reason: DisplayString,
    ) -> tuple[int, RollRecord]:
        """Roll a d20 tie-break with no DC or modifiers and create a record."""
        raw_roll = self._rng.roll(20)
        
        record = RollRecord(
            roll_id=self._id_generator(),
            transaction_id=transaction_id,
            revision=revision,
            recorded_at=self._clock(),
            command_id=command_id,
            reason=reason,
            die_sides=20,
            raw_rolls=[raw_roll],
            selected_roll_index=0,
            named_modifiers={},
            total=raw_roll,
            dc=None,
            difficulty=None,
            outcome=None,
            confirmed_effect_ids=[],
            supersedes_roll_id=None,
        )
        return raw_roll, record
