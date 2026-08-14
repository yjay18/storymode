"""Combat status effect definitions and start-turn processing registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import NamedTuple

from domain.models.combat_state import CombatParticipant
from domain.models.common import EntityId
from domain.models.runtime_common import StatusInstance
from domain.rules.combat_resources import apply_damage, apply_healing


class StatusProcessingResult(NamedTuple):
    """Result of processing a status on an actor."""

    actor: CombatParticipant
    updated_status: StatusInstance | None  # None if expired
    prevent_action: bool
    log_messages: list[str]


StatusHandlerFunc = Callable[[CombatParticipant, StatusInstance], StatusProcessingResult]


@dataclass(frozen=True)
class StatusDefinition:
    """Definition and priority of a combat status."""

    status_id: EntityId
    priority: int  # Lower values process earlier
    handler: StatusHandlerFunc


def _handle_guarded(actor: CombatParticipant, status: StatusInstance) -> StatusProcessingResult:
    """Guarded expires at the start of the actor's next turn."""
    duration = status.duration_remaining
    if duration is None or duration <= 1:
        return StatusProcessingResult(
            actor=actor,
            updated_status=None,
            prevent_action=False,
            log_messages=[f"Guarded expired on {actor.side} participant."],
        )
    return StatusProcessingResult(
        actor=actor,
        updated_status=status.model_copy(update={"duration_remaining": duration - 1}),
        prevent_action=False,
        log_messages=[],
    )


def _handle_dot(actor: CombatParticipant, status: StatusInstance) -> StatusProcessingResult:
    """Damage-over-time (Bleed / Poison / Burn) inflicts damage at turn start."""
    damage = status.magnitude if status.magnitude is not None else 1
    new_hp, new_armour, res = apply_damage(actor.hp, actor.armour, damage)
    updated_actor = actor.model_copy(update={"hp": new_hp, "armour": new_armour})

    duration = status.duration_remaining
    new_status: StatusInstance | None = None
    if duration is not None and duration > 1:
        new_status = status.model_copy(update={"duration_remaining": duration - 1})

    msg = (
        f"{status.status_id} dealt {damage} damage ({res.armour_absorbed} to armour, "
        f"{res.hp_damage} to HP). HP is now {new_hp.current}/{new_hp.maximum}."
    )

    return StatusProcessingResult(
        actor=updated_actor,
        updated_status=new_status,
        prevent_action=False,
        log_messages=[msg],
    )


def _handle_hot(actor: CombatParticipant, status: StatusInstance) -> StatusProcessingResult:
    """Healing-over-time (Regen) heals HP at turn start."""
    amount = status.magnitude if status.magnitude is not None else 1
    new_hp, healed = apply_healing(actor.hp, amount)
    updated_actor = actor.model_copy(update={"hp": new_hp})

    duration = status.duration_remaining
    new_status: StatusInstance | None = None
    if duration is not None and duration > 1:
        new_status = status.model_copy(update={"duration_remaining": duration - 1})

    msg = f"{status.status_id} restored {healed} HP. HP is now {new_hp.current}/{new_hp.maximum}."

    return StatusProcessingResult(
        actor=updated_actor,
        updated_status=new_status,
        prevent_action=False,
        log_messages=[msg],
    )


def _handle_incapacitated(
    actor: CombatParticipant, status: StatusInstance
) -> StatusProcessingResult:
    """Stun / Incapacitated prevents the actor from taking actions this turn."""
    duration = status.duration_remaining
    new_status: StatusInstance | None = None
    if duration is not None and duration > 1:
        new_status = status.model_copy(update={"duration_remaining": duration - 1})

    return StatusProcessingResult(
        actor=actor,
        updated_status=new_status,
        prevent_action=True,
        log_messages=[f"{status.status_id} prevented the actor from acting this turn."],
    )


def _handle_generic_buff_debuff(
    actor: CombatParticipant, status: StatusInstance
) -> StatusProcessingResult:
    """Generic duration-tracked buff or debuff (e.g. Exposed, Focus)."""
    duration = status.duration_remaining
    new_status: StatusInstance | None = None
    if duration is not None and duration > 1:
        new_status = status.model_copy(update={"duration_remaining": duration - 1})

    return StatusProcessingResult(
        actor=actor,
        updated_status=new_status,
        prevent_action=False,
        log_messages=[],
    )


# Closed registry of known statuses
STATUS_REGISTRY: dict[EntityId, StatusDefinition] = {
    EntityId("guarded"): StatusDefinition(
        status_id=EntityId("guarded"), priority=100, handler=_handle_guarded
    ),
    EntityId("bleed"): StatusDefinition(
        status_id=EntityId("bleed"), priority=10, handler=_handle_dot
    ),
    EntityId("poison"): StatusDefinition(
        status_id=EntityId("poison"), priority=10, handler=_handle_dot
    ),
    EntityId("burn"): StatusDefinition(
        status_id=EntityId("burn"), priority=10, handler=_handle_dot
    ),
    EntityId("regen"): StatusDefinition(
        status_id=EntityId("regen"), priority=20, handler=_handle_hot
    ),
    EntityId("stun"): StatusDefinition(
        status_id=EntityId("stun"), priority=30, handler=_handle_incapacitated
    ),
    EntityId("frozen"): StatusDefinition(
        status_id=EntityId("frozen"), priority=30, handler=_handle_incapacitated
    ),
    EntityId("exposed"): StatusDefinition(
        status_id=EntityId("exposed"), priority=40, handler=_handle_generic_buff_debuff
    ),
    EntityId("focus"): StatusDefinition(
        status_id=EntityId("focus"), priority=50, handler=_handle_generic_buff_debuff
    ),
}


def process_actor_statuses(
    actor: CombatParticipant,
) -> tuple[CombatParticipant, list[StatusInstance], bool, list[str]]:
    """Process start-of-turn statuses on a combat participant in stable priority order.

    Raises ValueError if an unknown status is encountered.
    Returns:
    - updated CombatParticipant
    - remaining active statuses list
    - prevent_action (True if any status prevented acting)
    - list of log messages
    """
    if not actor.statuses:
        return actor, [], False, []

    # Validate all statuses exist in registry first
    for s in actor.statuses:
        if s.status_id not in STATUS_REGISTRY:
            raise ValueError(f"Unknown status ID: {s.status_id}")

    # Sort statuses by (priority, status_id)
    sorted_statuses = sorted(
        actor.statuses,
        key=lambda s: (STATUS_REGISTRY[s.status_id].priority, s.status_id),
    )

    current_actor = actor
    remaining_statuses: list[StatusInstance] = []
    prevent_action = False
    all_logs: list[str] = []

    for s in sorted_statuses:
        definition = STATUS_REGISTRY[s.status_id]
        res = definition.handler(current_actor, s)
        current_actor = res.actor
        if res.updated_status is not None:
            remaining_statuses.append(res.updated_status)
        if res.prevent_action:
            prevent_action = True
        all_logs.extend(res.log_messages)

        # If actor dies during status processing, break early
        if current_actor.hp.current <= 0:
            break

    return current_actor, remaining_statuses, prevent_action, all_logs
