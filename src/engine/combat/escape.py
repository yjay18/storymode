"""Combat flee and yield resolution."""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.audit import RollRecord
from domain.models.campaign_meta import DefaultDifficulty
from domain.models.combat_state import CombatState, ParticipantSide
from domain.models.common import DisplayString, EntityId
from domain.rules.difficulty import DIFFICULTY_PROFILES
from engine.combat.consequences import AuthoredConsequence
from engine.dice.checks import ExplorationBand, calculate_exploration_band
from engine.dice.service import DiceService


@dataclass(frozen=True)
class EscapePolicyDefinition:
    """Authored escape configuration for an encounter."""

    id: EntityId
    dc: int
    consequences: dict[ExplorationBand, AuthoredConsequence]
    ends_combat_on_success: bool = True
    ends_combat_on_partial: bool = True


@dataclass(frozen=True)
class YieldPolicyDefinition:
    """Authored yield configuration for an encounter."""

    id: EntityId
    allowed: bool
    consequence: AuthoredConsequence


@dataclass(frozen=True)
class FleeExecutionResult:
    """Result of attempting to flee combat."""

    success: bool
    combat_ended: bool
    band: ExplorationBand
    roll: int
    roll_record: RollRecord
    updated_combat: CombatState | None
    consequence_applied: AuthoredConsequence | None
    logs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class YieldExecutionResult:
    """Result of yielding in combat."""

    success: bool
    combat_ended: bool
    consequence_applied: AuthoredConsequence
    logs: list[str] = field(default_factory=list)


def execute_flee_command(
    combat: CombatState,
    actor_id: EntityId,
    escape_policy: EscapePolicyDefinition,
    dice_service: DiceService,
    difficulty: DefaultDifficulty = DefaultDifficulty.NORMAL,
    dexterity_modifier: int = 0,
    named_modifiers: dict[DisplayString, int] | None = None,
    transaction_id: EntityId | None = None,
    revision: int = 1,
    command_id: EntityId | None = None,
) -> FleeExecutionResult:
    """Validate and execute a flee command using the encounter's authored escape policy."""
    # 1. Turn order check
    if not combat.order or combat.order[combat.current_index] != actor_id:
        current_expected = combat.order[combat.current_index] if combat.order else "None"
        raise ValueError(f"Not {actor_id}'s turn. Current active actor is {current_expected}.")

    # 2. Actor living and side check
    if actor_id not in combat.participants:
        raise ValueError(f"Actor {actor_id} not found in combat participants")

    actor = combat.participants[actor_id]
    if actor.hp.current <= 0:
        raise ValueError(f"Actor {actor_id} is defeated and cannot act")

    if actor.side != ParticipantSide.PARTY:
        raise ValueError(f"Only party members may execute flee, actor {actor_id} is {actor.side}")

    # 3. Status check
    incapacitated_statuses = {EntityId("stun"), EntityId("frozen")}
    for s in actor.statuses:
        if s.status_id in incapacitated_statuses:
            raise ValueError(
                f"Actor {actor_id} is incapacitated by '{s.status_id}' and cannot flee"
            )

    # 4. Difficulty-adjusted DC
    diff_profile = DIFFICULTY_PROFILES[difficulty]
    adjusted_dc = escape_policy.dc + diff_profile.dc_adjustment

    # 5. Modifiers
    all_named_mods = dict(named_modifiers or {})
    if dexterity_modifier != 0:
        all_named_mods[DisplayString("Dexterity")] = dexterity_modifier

    tx_id = transaction_id or EntityId("tx_flee")
    cmd_id = command_id or EntityId("cmd_flee")
    reason = DisplayString("Flee escape check")

    # 6. Execute check
    total, roll_rec = dice_service.roll_exploration_check(
        transaction_id=tx_id,
        revision=revision,
        command_id=cmd_id,
        reason=reason,
        dc=adjusted_dc,
        difficulty=difficulty,
        named_modifiers=all_named_mods,
    )

    raw_roll = roll_rec.raw_rolls[0]
    band = calculate_exploration_band(raw_roll, total, adjusted_dc)

    is_success_band = band in {ExplorationBand.CRITICAL_SUCCESS, ExplorationBand.SUCCESS}
    is_partial = band == ExplorationBand.PARTIAL_SUCCESS

    combat_ended = (is_success_band and escape_policy.ends_combat_on_success) or (
        is_partial and escape_policy.ends_combat_on_partial
    )

    consequence = escape_policy.consequences.get(band)

    logs: list[str] = [
        f"{actor_id} attempted to flee: rolled {raw_roll} "
        f"(total {total} vs DC {adjusted_dc}) -> {band.value}."
    ]
    if consequence:
        logs.append(str(consequence.description))

    updated_combat: CombatState | None = None if combat_ended else combat

    return FleeExecutionResult(
        success=is_success_band or is_partial,
        combat_ended=combat_ended,
        band=band,
        roll=total,
        roll_record=roll_rec,
        updated_combat=updated_combat,
        consequence_applied=consequence,
        logs=logs,
    )


def execute_yield_command(
    combat: CombatState,
    actor_id: EntityId,
    yield_policy: YieldPolicyDefinition,
) -> YieldExecutionResult:
    """Validate and execute a yield command without rolling dice."""
    # 1. Turn order check
    if not combat.order or combat.order[combat.current_index] != actor_id:
        current_expected = combat.order[combat.current_index] if combat.order else "None"
        raise ValueError(f"Not {actor_id}'s turn. Current active actor is {current_expected}.")

    # 2. Actor living and side check
    if actor_id not in combat.participants:
        raise ValueError(f"Actor {actor_id} not found in combat participants")

    actor = combat.participants[actor_id]
    if actor.hp.current <= 0:
        raise ValueError(f"Actor {actor_id} is defeated and cannot act")

    if actor.side != ParticipantSide.PARTY:
        raise ValueError(f"Only party members may yield, actor {actor_id} is {actor.side}")

    # 3. Policy permission
    if not yield_policy.allowed:
        raise ValueError("Yielding is not permitted in this encounter.")

    logs: list[str] = [
        f"{actor_id} yielded to the enemy.",
        str(yield_policy.consequence.description),
    ]

    return YieldExecutionResult(
        success=True,
        combat_ended=True,
        consequence_applied=yield_policy.consequence,
        logs=logs,
    )
