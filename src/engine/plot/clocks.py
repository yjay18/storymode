"""Event-driven progress and threat clocks (PLOT-04).

No system clock, time, or wall-clock imports allowed in this package.
Clocks advance strictly in response to committed engine events.
"""

from __future__ import annotations

from typing import Literal

from domain.models.common import DisplayString, EntityId, FrozenModel
from domain.models.plot import ClockDefinition
from domain.models.plot_state import ClockState
from domain.models.runtime_state import RuntimeState


class ClockAdvancementResult(FrozenModel):
    """Summary of advancing a clock."""

    clock_id: EntityId
    previous_value: int
    new_value: int
    maximum: int
    just_completed: bool
    completion_effect_ids: list[EntityId]


class PairedChallengeResult(FrozenModel):
    """Result of evaluating a paired success/complication challenge."""

    success_clock_id: EntityId
    complication_clock_id: EntityId
    is_resolved: bool
    winner: Literal["success", "complication", "none"]


def initialize_clock(clock_def: ClockDefinition, state: RuntimeState) -> RuntimeState:
    """Initialize a clock in runtime state if not present."""
    if clock_def.id in state.clocks:
        return state

    clock = ClockState(
        clock_id=clock_def.id,
        current=0,
        maximum=clock_def.maximum,
        completed=False,
        last_advancement_revision=state.revision,
    )
    new_clocks = {**state.clocks, clock_def.id: clock}
    return state.model_copy(update={"clocks": new_clocks})


def advance_clock(
    state: RuntimeState,
    clock_id: EntityId,
    clock_def: ClockDefinition,
    amount: int = 1,
) -> tuple[RuntimeState, ClockAdvancementResult]:
    """Advance a clock by an amount (capped at maximum) and apply completion effects if completed.

    Raises ValueError if:
    - amount < 1
    - clock_id mismatch
    """
    if amount < 1:
        raise ValueError(f"Advancement amount must be >= 1, got {amount}")

    if clock_def.id != clock_id:
        raise ValueError(f"Clock definition mismatch: {clock_def.id} != {clock_id}")

    clock = state.clocks.get(clock_id)
    if clock is None:
        clock = ClockState(
            clock_id=clock_id,
            current=0,
            maximum=clock_def.maximum,
            completed=False,
            last_advancement_revision=state.revision,
        )

    prev_val = clock.current
    new_val = min(clock.maximum, prev_val + amount)
    just_completed = (not clock.completed) and (new_val >= clock.maximum)
    is_completed = clock.completed or just_completed

    new_clock = clock.model_copy(
        update={
            "current": new_val,
            "completed": is_completed,
            "last_advancement_revision": state.revision,
        }
    )

    new_facts = set(state.known_fact_ids)
    applied_effects: list[EntityId] = []
    if just_completed:
        for eff_id in clock_def.completion_effect_ids:
            new_facts.add(eff_id)
            applied_effects.append(eff_id)

    new_clocks = {**state.clocks, clock_id: new_clock}
    new_state = state.model_copy(update={"clocks": new_clocks, "known_fact_ids": new_facts})

    result = ClockAdvancementResult(
        clock_id=clock_id,
        previous_value=prev_val,
        new_value=new_val,
        maximum=clock.maximum,
        just_completed=just_completed,
        completion_effect_ids=applied_effects,
    )
    return new_state, result


def process_event_clocks(
    state: RuntimeState,
    event_type: str | DisplayString,
    clock_defs: list[ClockDefinition],
    amount: int = 1,
) -> tuple[RuntimeState, list[ClockAdvancementResult]]:
    """Process a committed event type across all matching active clocks."""
    current_state = state
    results: list[ClockAdvancementResult] = []
    ev_str = str(event_type).strip().lower()

    # Ignored non-trigger events (reading, inventory management, dialogue display)
    ignored_event_prefixes = (
        "read",
        "view",
        "inventory",
        "dialogue",
        "dialog",
        "inspect",
        "browse",
    )
    if any(ev_str.startswith(prefix) for prefix in ignored_event_prefixes):
        return current_state, []

    for c_def in clock_defs:
        matches = any(str(t).strip().lower() == ev_str for t in c_def.trigger_event_types)
        if matches:
            current_state, res = advance_clock(current_state, c_def.id, c_def, amount=amount)
            results.append(res)

    return current_state, results


def evaluate_paired_challenge(
    state: RuntimeState,
    success_clock_id: EntityId,
    complication_clock_id: EntityId,
) -> PairedChallengeResult:
    """Evaluate completion order for a paired success/complication challenge."""
    s_clk = state.clocks.get(success_clock_id)
    c_clk = state.clocks.get(complication_clock_id)

    s_done = s_clk is not None and s_clk.completed
    c_done = c_clk is not None and c_clk.completed

    if not s_done and not c_done:
        return PairedChallengeResult(
            success_clock_id=success_clock_id,
            complication_clock_id=complication_clock_id,
            is_resolved=False,
            winner="none",
        )

    if s_done and not c_done:
        return PairedChallengeResult(
            success_clock_id=success_clock_id,
            complication_clock_id=complication_clock_id,
            is_resolved=True,
            winner="success",
        )

    if c_done and not s_done:
        return PairedChallengeResult(
            success_clock_id=success_clock_id,
            complication_clock_id=complication_clock_id,
            is_resolved=True,
            winner="complication",
        )

    # Both completed: determine winner by last_advancement_revision
    assert s_clk is not None and c_clk is not None
    if s_clk.last_advancement_revision < c_clk.last_advancement_revision:
        winner: Literal["success", "complication"] = "success"
    else:
        winner = "complication"

    return PairedChallengeResult(
        success_clock_id=success_clock_id,
        complication_clock_id=complication_clock_id,
        is_resolved=True,
        winner=winner,
    )
