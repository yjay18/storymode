"""Opportunity frontier management, state transitions, and audit tracking (PLOT-02)."""

from __future__ import annotations

import enum

from domain.models.common import DisplayString, EntityId, FrozenModel
from domain.models.plot import OpportunityDefinition, PlotFile
from domain.models.plot_state import OpportunityInstance
from domain.models.runtime_state import RuntimeState
from engine.plot.predicates import evaluate_all_predicates


class OpportunityStatus(enum.StrEnum):
    """The runtime status of an opportunity in the frontier."""

    ACTIVE = "active"
    DEFERRED = "deferred"
    LOCKED = "locked"
    INVALIDATED = "invalidated"
    RESOLVED = "resolved"


class FrontierDiagnostic(FrozenModel):
    """Diagnostic report for the opportunity frontier."""

    active_count: int
    deferred_count: int
    locked_count: int
    invalidated_count: int
    resolved_count: int
    is_ending: bool
    is_below_minimum: bool
    warning: DisplayString | None = None


class OpportunityResolutionResult(FrozenModel):
    """Summary of a resolved opportunity."""

    opportunity_id: EntityId
    outcome_id: EntityId
    parent_milestone_id: EntityId | None
    is_resolved: bool


def _get_opportunity_def(
    opportunity_id: EntityId,
    plot_file: PlotFile,
) -> OpportunityDefinition | None:
    for opp in plot_file.authored_opportunities:
        if opp.id == opportunity_id:
            return opp
    return None


def evaluate_opportunity_status(
    opp_def: OpportunityDefinition,
    instance: OpportunityInstance | None,
    state: RuntimeState,
) -> OpportunityStatus:
    """Determine the current status of an opportunity against runtime state."""
    if instance is not None and instance.is_resolved:
        return OpportunityStatus.RESOLVED

    # Check expiry/invalidation conditions
    for exp in opp_def.expiry_conditions:
        if evaluate_all_predicates([exp], state):
            return OpportunityStatus.INVALIDATED

    # Check parent milestone reachability/activity
    parent_m = opp_def.parent_milestone_id
    if parent_m not in state.plot.current_milestone_ids:
        return OpportunityStatus.LOCKED

    # Check preconditions
    if not evaluate_all_predicates(opp_def.preconditions, state):
        return OpportunityStatus.LOCKED

    return OpportunityStatus.ACTIVE


def sync_opportunity_frontier(
    state: RuntimeState,
    plot_file: PlotFile,
) -> tuple[RuntimeState, FrontierDiagnostic]:
    """Synchronize the opportunity frontier, maintaining target 3-7 active opportunities.

    - Defer rather than delete unchosen opportunities.
    - Invalidate only on explicit satisfied expiry predicates.
    - Cap active opportunities at 7 (excess deferred).
    - Produce diagnostics if active count falls below 3.
    """
    updated_opps: dict[EntityId, OpportunityInstance] = dict(state.plot.opportunities)
    active_candidates: list[EntityId] = []
    deferred_count = 0
    locked_count = 0
    invalidated_count = 0
    resolved_count = 0

    # 1. Process all authored opportunities for active milestones
    for opp_def in plot_file.authored_opportunities:
        opp_id = opp_def.id
        instance = updated_opps.get(opp_id)

        status = evaluate_opportunity_status(opp_def, instance, state)

        if status == OpportunityStatus.RESOLVED:
            resolved_count += 1
            if instance is None:
                updated_opps[opp_id] = OpportunityInstance(
                    opportunity_id=opp_id,
                    parent_id=opp_def.parent_milestone_id,
                    origin_id=opp_id,
                    is_resolved=True,
                )
        elif status == OpportunityStatus.INVALIDATED:
            invalidated_count += 1
        elif status == OpportunityStatus.LOCKED:
            locked_count += 1
        elif status == OpportunityStatus.ACTIVE:
            active_candidates.append(opp_id)
            if instance is None:
                updated_opps[opp_id] = OpportunityInstance(
                    opportunity_id=opp_id,
                    parent_id=opp_def.parent_milestone_id,
                    origin_id=opp_id,
                    is_resolved=False,
                )

    # 2. Bound active count to 3-7
    # If active count > 7, defer lowest priority (excess)
    max_active = 7
    active_ids = active_candidates[:max_active]
    deferred_ids = active_candidates[max_active:]
    deferred_count += len(deferred_ids)

    active_count = len(active_ids)
    is_ending = bool(state.plot.ending_state) or any(
        m in plot_file.ending_milestone_ids for m in state.plot.current_milestone_ids
    )

    is_below_min = active_count < 3
    warning_msg = None
    if is_below_min and not is_ending:
        warning_msg = DisplayString(
            f"Opportunity frontier below minimum: {active_count} active (target 3-7)."
        )

    new_plot = state.plot.model_copy(update={"opportunities": updated_opps})
    new_state = state.model_copy(update={"plot": new_plot})

    diagnostic = FrontierDiagnostic(
        active_count=active_count,
        deferred_count=deferred_count,
        locked_count=locked_count,
        invalidated_count=invalidated_count,
        resolved_count=resolved_count,
        is_ending=is_ending,
        is_below_minimum=is_below_min,
        warning=warning_msg,
    )

    return new_state, diagnostic


def resolve_opportunity(
    state: RuntimeState,
    opportunity_id: EntityId,
    outcome_id: EntityId,
    plot_file: PlotFile,
) -> tuple[RuntimeState, OpportunityResolutionResult]:
    """Resolve an opportunity with an authorized outcome and commit the fact."""
    opp_def = _get_opportunity_def(opportunity_id, plot_file)
    instance = state.plot.opportunities.get(opportunity_id)

    if instance is not None and instance.is_resolved:
        raise ValueError(f"Opportunity '{opportunity_id}' is already resolved")

    if opp_def is not None and outcome_id not in opp_def.allowed_outcome_ids:
        raise ValueError(
            f"Outcome '{outcome_id}' is not in allowed outcomes for opportunity '{opportunity_id}':"
            f" {opp_def.allowed_outcome_ids}"
        )

    parent_id = (
        opp_def.parent_milestone_id if opp_def else (instance.parent_id if instance else None)
    )
    new_instance = OpportunityInstance(
        opportunity_id=opportunity_id,
        parent_id=parent_id,
        origin_id=instance.origin_id if instance else opportunity_id,
        predecessor_id=instance.predecessor_id if instance else None,
        is_resolved=True,
    )

    new_opps = {**state.plot.opportunities, opportunity_id: new_instance}
    new_facts = set(state.known_fact_ids)
    new_facts.add(outcome_id)

    new_plot = state.plot.model_copy(update={"opportunities": new_opps})
    new_state = state.model_copy(update={"plot": new_plot, "known_fact_ids": new_facts})

    # Sync frontier after resolution
    synced_state, _ = sync_opportunity_frontier(new_state, plot_file)

    result = OpportunityResolutionResult(
        opportunity_id=opportunity_id,
        outcome_id=outcome_id,
        parent_milestone_id=parent_id,
        is_resolved=True,
    )

    return synced_state, result


def transform_opportunity(
    state: RuntimeState,
    previous_id: EntityId,
    new_opportunity: OpportunityInstance,
) -> RuntimeState:
    """Transform an opportunity into a successor, tracking predecessor_id."""
    instance_with_pred = new_opportunity.model_copy(update={"predecessor_id": previous_id})
    new_opps = {
        **state.plot.opportunities,
        new_opportunity.opportunity_id: instance_with_pred,
    }
    new_plot = state.plot.model_copy(update={"opportunities": new_opps})
    return state.model_copy(update={"plot": new_plot})
