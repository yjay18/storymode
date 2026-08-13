"""Decision and management of pending checks."""

import uuid
from typing import Any

from domain.models.check_state import CheckOutcomes, PendingCheck
from domain.models.common import EntityId
from domain.models.runtime_state import RuntimeState
from engine.actions.protocols import ActionProposalLike


def decide_check_necessity(proposal: ActionProposalLike) -> bool:
    """Decide if a proposal requires a check based on challenge label."""
    return proposal.challenge_label != "none"


def build_pending_check(
    command_id: EntityId,
    state: RuntimeState,
    proposal: ActionProposalLike,
    base_dc: int,
    difficulty_adjustment: int,
    actor_id: EntityId,
    target_ids: list[EntityId],
    outcomes: CheckOutcomes,
) -> PendingCheck:
    """Map a proposal's challenge and stakes into a PendingCheck."""
    stakes_str = " | ".join(proposal.stakes) if proposal.stakes else "None"
    
    # Use verb or intended effect as original input representation for now
    original_input = proposal.intended_effect
    
    return PendingCheck(
        check_id=f"chk-{uuid.uuid4().hex[:8]}",
        source_command_id=command_id,
        source_revision=state.revision,
        original_input=original_input,
        resolved_operation=proposal.operation,
        actor_id=actor_id,
        target_ids=target_ids,
        semantic_difficulty=proposal.challenge_label,
        base_dc=base_dc,
        difficulty_adjustment=difficulty_adjustment,
        final_dc=base_dc + difficulty_adjustment,
        stakes=stakes_str,
        allowed_outcomes=outcomes,
    )


def cancel_pending_check(state: RuntimeState) -> RuntimeState:
    """Cancel the active pending check.
    
    This clears the check in a normal revision and consumes no die.
    """
    if not state.pending_check:
        raise ValueError("No active pending check to cancel")
        
    return state.model_copy(update={"pending_check": None})
