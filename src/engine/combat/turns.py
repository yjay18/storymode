"""Combat turn advancement, turn-start mana regeneration, and status processing."""

from __future__ import annotations

from domain.models.combat_state import CombatState, ParticipantSide
from domain.models.common import EntityId
from domain.rules.combat_resources import apply_mana_delta
from engine.combat.statuses import process_actor_statuses


def is_side_defeated(combat: CombatState, side: ParticipantSide) -> bool:
    """Check if all participants on the given side have 0 HP."""
    side_participants = [p for p in combat.participants.values() if p.side == side]
    if not side_participants:
        return True
    return all(p.hp.current == 0 for p in side_participants)


def process_turn_start(
    combat: CombatState,
    actor_id: EntityId,
    mana_regen: int = 0,
) -> tuple[CombatState, bool, list[str]]:
    """Execute turn-start steps for an active actor:

    1. Process active status effects in (priority, status_id) order.
    2. If actor remains alive, regenerate mana up to maximum capacity.
    3. Return updated CombatState, whether the actor can take an action, and event logs.
    """
    if actor_id not in combat.participants:
        raise ValueError(f"Actor {actor_id} not found in combat participants")

    actor = combat.participants[actor_id]

    # Process statuses
    updated_actor, remaining_statuses, prevent_action, status_logs = process_actor_statuses(actor)
    all_logs = list(status_logs)

    # If actor died from status effects
    if updated_actor.hp.current == 0:
        updated_actor = updated_actor.model_copy(update={"statuses": remaining_statuses})
        new_participants = dict(combat.participants)
        new_participants[actor_id] = updated_actor
        return (
            combat.model_copy(update={"participants": new_participants}),
            False,
            all_logs,
        )

    # Regenerate mana if alive
    if mana_regen > 0:
        new_mana, actual_gain = apply_mana_delta(updated_actor.mana, mana_regen)
        updated_actor = updated_actor.model_copy(
            update={"mana": new_mana, "statuses": remaining_statuses}
        )
        if actual_gain > 0:
            all_logs.append(
                f"{actor_id} regenerated {actual_gain} mana "
                f"({new_mana.current}/{new_mana.maximum})."
            )
    else:
        updated_actor = updated_actor.model_copy(update={"statuses": remaining_statuses})

    new_participants = dict(combat.participants)
    new_participants[actor_id] = updated_actor

    can_act = not prevent_action

    return (
        combat.model_copy(update={"participants": new_participants}),
        can_act,
        all_logs,
    )


def advance_turn(
    combat: CombatState,
    mana_regen_by_id: dict[EntityId, int] | None = None,
) -> tuple[CombatState, EntityId | None, bool, list[str]]:
    """Advance combat to the next living participant's turn.

    Iterates through the turn order, increments the round counter when completing a full cycle,
    skips defeated actors, and processes turn-start effects on the next eligible actor.

    Returns:
    - updated CombatState
    - active actor ID (None if combat is over)
    - can_act (True if actor can select an action)
    - list of accumulated event logs
    """
    mana_map = mana_regen_by_id or {}
    all_logs: list[str] = []
    current_combat = combat

    # Check side defeat
    if is_side_defeated(current_combat, ParticipantSide.ENEMY):
        return current_combat, None, False, ["All enemies are defeated."]
    if is_side_defeated(current_combat, ParticipantSide.PARTY):
        return current_combat, None, False, ["All party members are defeated."]

    order_len = len(current_combat.order)
    if order_len == 0:
        return current_combat, None, False, []

    # Advance index
    next_index = current_combat.current_index + 1
    next_round = current_combat.round
    if next_index >= order_len:
        next_index = 0
        next_round += 1
        all_logs.append(f"Round {next_round} begins.")

    current_combat = current_combat.model_copy(
        update={"current_index": next_index, "round": next_round}
    )

    # Search for next living actor
    attempts = 0
    while attempts < order_len:
        actor_id = current_combat.order[current_combat.current_index]
        actor = current_combat.participants[actor_id]

        if actor.hp.current > 0:
            # Found living actor, process turn start
            regen = mana_map.get(actor_id, 0)
            updated_combat, can_act, turn_logs = process_turn_start(
                current_combat, actor_id, mana_regen=regen
            )
            all_logs.extend(turn_logs)
            current_combat = updated_combat

            # Check if actor died during turn start (e.g. DoT)
            if current_combat.participants[actor_id].hp.current > 0:
                # Still alive, ready to act or skipped due to stun
                return current_combat, actor_id, can_act, all_logs

            # Actor died during turn start, check if combat ended
            if is_side_defeated(current_combat, ParticipantSide.ENEMY):
                return current_combat, None, False, all_logs
            if is_side_defeated(current_combat, ParticipantSide.PARTY):
                return current_combat, None, False, all_logs

        # Advance to next candidate
        next_index = current_combat.current_index + 1
        next_round = current_combat.round
        if next_index >= order_len:
            next_index = 0
            next_round += 1
            all_logs.append(f"Round {next_round} begins.")

        current_combat = current_combat.model_copy(
            update={"current_index": next_index, "round": next_round}
        )
        attempts += 1

    return current_combat, None, False, all_logs
