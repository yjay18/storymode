"""Milestone state transitions, precondition checks, and spine progression (PLOT-01)."""

from __future__ import annotations

from domain.models.common import DisplayString, EntityId, FrozenModel
from domain.models.plot import MilestoneDefinition, PlotFile
from domain.models.plot_state import MilestoneState
from domain.models.runtime_state import RuntimeState
from engine.plot.predicates import evaluate_all_predicates


class MilestoneResolutionResult(FrozenModel):
    """Summary of a resolved milestone."""

    milestone_id: EntityId
    outcome_id: EntityId
    unlocked_next_milestone_ids: list[EntityId]
    is_campaign_ending: bool


def _get_milestone_def(milestone_id: EntityId, plot_file: PlotFile) -> MilestoneDefinition:
    for m in plot_file.milestones:
        if m.id == milestone_id:
            return m
    raise ValueError(f"Milestone '{milestone_id}' not found in campaign plot definition")


def initialize_plot_state(plot_file: PlotFile, state: RuntimeState) -> RuntimeState:
    """Initialize milestone states for a new or uninitialized plot."""
    milestones: dict[EntityId, MilestoneState] = {}
    current_ids: set[EntityId] = set()

    for m in plot_file.milestones:
        if m.id in plot_file.start_milestone_ids:
            if evaluate_all_predicates(m.preconditions, state):
                milestones[m.id] = MilestoneState.AVAILABLE
            else:
                milestones[m.id] = MilestoneState.LOCKED
        else:
            milestones[m.id] = MilestoneState.LOCKED

    new_plot = state.plot.model_copy(
        update={"milestones": milestones, "current_milestone_ids": current_ids}
    )
    return state.model_copy(update={"plot": new_plot})


def activate_milestone(
    state: RuntimeState,
    milestone_id: EntityId,
    plot_file: PlotFile,
) -> RuntimeState:
    """Transition a milestone from AVAILABLE to ACTIVE.

    Raises ValueError if:
    - milestone is unknown
    - milestone is already resolved/failed
    - milestone is currently locked
    - preconditions are not satisfied
    """
    m_def = _get_milestone_def(milestone_id, plot_file)
    current_status = state.plot.milestones.get(milestone_id, MilestoneState.LOCKED)

    if current_status == MilestoneState.ACTIVE:
        return state  # Idempotent

    if current_status == MilestoneState.RESOLVED and not m_def.cycle_allowed:
        raise ValueError(f"Milestone '{milestone_id}' is already resolved and cycles are forbidden")

    if current_status == MilestoneState.FAILED:
        raise ValueError(f"Milestone '{milestone_id}' has already failed")

    if current_status == MilestoneState.LOCKED and not evaluate_all_predicates(
        m_def.preconditions, state
    ):
        raise ValueError(
            f"Cannot activate locked milestone '{milestone_id}': preconditions not met"
        )

    if not evaluate_all_predicates(m_def.preconditions, state):
        raise ValueError(f"Preconditions not met for activating milestone '{milestone_id}'")

    new_milestones = {**state.plot.milestones, milestone_id: MilestoneState.ACTIVE}
    new_current = set(state.plot.current_milestone_ids)
    new_current.add(milestone_id)

    new_plot = state.plot.model_copy(
        update={"milestones": new_milestones, "current_milestone_ids": new_current}
    )
    return state.model_copy(update={"plot": new_plot})


def resolve_milestone(
    state: RuntimeState,
    milestone_id: EntityId,
    outcome_id: EntityId,
    plot_file: PlotFile,
) -> tuple[RuntimeState, MilestoneResolutionResult]:
    """Resolve an active milestone with an authorized outcome and advance spine.

    Validates:
    - outcome_id is in required_outcome_ids
    - forbidden_changes are respected
    - milestone is currently ACTIVE or AVAILABLE
    """
    m_def = _get_milestone_def(milestone_id, plot_file)
    current_status = state.plot.milestones.get(milestone_id, MilestoneState.LOCKED)

    if current_status not in (MilestoneState.ACTIVE, MilestoneState.AVAILABLE):
        raise ValueError(f"Cannot resolve milestone '{milestone_id}' in state '{current_status}'")

    if outcome_id not in m_def.required_outcome_ids:
        raise ValueError(
            f"Outcome '{outcome_id}' is not in required outcomes for milestone '{milestone_id}':"
            f" {m_def.required_outcome_ids}"
        )

    # Validate forbidden changes: if an outcome or forbidden change matches a forbidden rule, reject
    for forbidden in m_def.forbidden_changes:
        f_text = str(forbidden).strip()
        if f_text and (f_text == str(outcome_id) or f_text in state.known_fact_ids):
            raise ValueError(f"Resolution violates forbidden change: '{forbidden}'")

    new_milestones = {**state.plot.milestones, milestone_id: MilestoneState.RESOLVED}
    new_current = {m for m in state.plot.current_milestone_ids if m != milestone_id}
    new_facts = set(state.known_fact_ids)
    new_facts.add(outcome_id)

    # Unlock valid next milestones
    unlocked_next: list[EntityId] = []
    temp_state = state.model_copy(
        update={
            "known_fact_ids": new_facts,
            "plot": state.plot.model_copy(
                update={"milestones": new_milestones, "current_milestone_ids": new_current}
            ),
        }
    )

    for next_id in m_def.valid_next_milestone_ids:
        next_def = _get_milestone_def(next_id, plot_file)
        next_status = new_milestones.get(next_id, MilestoneState.LOCKED)
        if (
            next_status == MilestoneState.LOCKED
            or (next_status == MilestoneState.RESOLVED and next_def.cycle_allowed)
        ) and evaluate_all_predicates(next_def.preconditions, temp_state):
            new_milestones[next_id] = MilestoneState.AVAILABLE
            unlocked_next.append(next_id)

    is_ending = milestone_id in plot_file.ending_milestone_ids
    ending_str = None
    if is_ending:
        ending_str = DisplayString(
            f"Campaign completed via milestone '{milestone_id}' outcome '{outcome_id}'"
        )

    new_plot = state.plot.model_copy(
        update={
            "milestones": new_milestones,
            "current_milestone_ids": new_current,
            "ending_state": ending_str or state.plot.ending_state,
        }
    )
    final_state = state.model_copy(update={"plot": new_plot, "known_fact_ids": new_facts})

    result = MilestoneResolutionResult(
        milestone_id=milestone_id,
        outcome_id=outcome_id,
        unlocked_next_milestone_ids=unlocked_next,
        is_campaign_ending=is_ending,
    )

    return final_state, result


def fail_milestone(
    state: RuntimeState,
    milestone_id: EntityId,
    plot_file: PlotFile,
) -> RuntimeState:
    """Transition an active/available milestone to FAILED."""
    _get_milestone_def(milestone_id, plot_file)
    current_status = state.plot.milestones.get(milestone_id, MilestoneState.LOCKED)

    if current_status not in (MilestoneState.ACTIVE, MilestoneState.AVAILABLE):
        raise ValueError(f"Cannot fail milestone '{milestone_id}' in state '{current_status}'")

    new_milestones = {**state.plot.milestones, milestone_id: MilestoneState.FAILED}
    new_current = {m for m in state.plot.current_milestone_ids if m != milestone_id}

    new_plot = state.plot.model_copy(
        update={"milestones": new_milestones, "current_milestone_ids": new_current}
    )
    return state.model_copy(update={"plot": new_plot})
