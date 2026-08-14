"""Combat Defend action and Guarded status management."""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.combat_state import CombatState
from domain.models.common import EntityId
from domain.models.runtime_common import StatusInstance


@dataclass(frozen=True)
class DefendExecutionResult:
    """Result of taking the Defend action."""

    success: bool
    actor_id: EntityId
    combat_state: CombatState
    logs: list[str] = field(default_factory=list)


def execute_defend_command(
    combat: CombatState,
    actor_id: EntityId,
) -> DefendExecutionResult:
    """Validate and execute the Defend action.

    Applies the non-stacking Guarded status to the actor (lasts until start of next turn).
    Costs 0 mana. If already Guarded, refreshes duration to 1.
    """
    # 1. Turn order check
    if not combat.order or combat.order[combat.current_index] != actor_id:
        current_expected = combat.order[combat.current_index] if combat.order else "None"
        raise ValueError(f"Not {actor_id}'s turn. Current active actor is {current_expected}.")

    # 2. Actor existence and living check
    if actor_id not in combat.participants:
        raise ValueError(f"Actor {actor_id} not found in combat participants")

    actor = combat.participants[actor_id]
    if actor.hp.current <= 0:
        raise ValueError(f"Actor {actor_id} is defeated and cannot act")

    # 3. Status prevention (incapacitation check)
    incapacitated_statuses = {EntityId("stun"), EntityId("frozen")}
    for s in actor.statuses:
        if s.status_id in incapacitated_statuses:
            raise ValueError(f"Actor {actor_id} is incapacitated by '{s.status_id}' and cannot act")

    # 4. Apply or refresh Guarded status
    statuses = list(actor.statuses)
    guarded_idx = next(
        (i for i, s in enumerate(statuses) if s.status_id == EntityId("guarded")),
        None,
    )

    if guarded_idx is not None:
        # Refresh duration to 1 without stacking
        statuses[guarded_idx] = StatusInstance(status_id=EntityId("guarded"), duration_remaining=1)
        log_msg = f"{actor_id} refreshed defensive stance (Guarded)."
    else:
        statuses.append(StatusInstance(status_id=EntityId("guarded"), duration_remaining=1))
        log_msg = f"{actor_id} took a defensive stance (Guarded for 1 turn)."

    new_actor = actor.model_copy(update={"statuses": statuses})
    new_participants = dict(combat.participants)
    new_participants[actor_id] = new_actor

    updated_combat = combat.model_copy(update={"participants": new_participants})

    return DefendExecutionResult(
        success=True,
        actor_id=actor_id,
        combat_state=updated_combat,
        logs=[log_msg],
    )
