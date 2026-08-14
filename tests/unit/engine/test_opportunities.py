"""Tests for opportunity frontier transitions and management (PLOT-02)."""

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.common import DisplayString, EntityId
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot import MilestoneDefinition, OpportunityDefinition, PlotFile
from domain.models.plot_state import MilestoneState, OpportunityInstance, PlotState
from domain.models.runtime_common import ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.world_state import LocationState
from engine.plot.opportunities import (
    OpportunityStatus,
    evaluate_opportunity_status,
    resolve_opportunity,
    sync_opportunity_frontier,
    transform_opportunity,
)

# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

_STATS = StatBlock(
    strength=10,
    dexterity=10,
    intelligence=10,
    charisma=10,
    constitution=10,
    wisdom=10,
)
_RES = ResourceValue(current=10, maximum=10)
_ZERO = ResourceValue(current=0, maximum=5)


def _make_opp_def(
    opp_id: str,
    parent_id: str = "m_start",
    preconditions: list[str] | None = None,
    expiry_conditions: list[str] | None = None,
    allowed_outcomes: list[str] | None = None,
) -> OpportunityDefinition:
    return OpportunityDefinition(
        id=EntityId(opp_id),
        parent_milestone_id=EntityId(parent_id),
        title=DisplayString(opp_id.title()),
        description=DisplayString("Description"),
        referenced_entity_ids=[],
        allowed_outcome_ids=[EntityId(o) for o in (allowed_outcomes or [f"outcome_{opp_id}"])],
        preconditions=[DisplayString(p) for p in (preconditions or [])],
        expiry_conditions=[DisplayString(e) for e in (expiry_conditions or [])],
        balance_rating=50,
    )


def _make_plot_file(
    opportunities: list[OpportunityDefinition],
    milestone_id: str = "m_start",
) -> PlotFile:
    m = MilestoneDefinition(
        id=EntityId(milestone_id),
        canonical_truth=DisplayString("Truth"),
        narrative_purpose=DisplayString("Purpose"),
        required_outcome_ids=[EntityId(f"out_{milestone_id}")],
        allowed_approach_tags=[],
        forbidden_changes=[],
        preconditions=[],
        valid_next_milestone_ids=[],
        difficulty_band=DisplayString("standard"),
        pacing_weight=50,
        cycle_allowed=False,
    )
    return PlotFile(
        campaign_id=EntityId("camp"),
        campaign_version="1.0.0",
        start_milestone_ids=[EntityId(milestone_id)],
        milestones=[m],
        authored_opportunities=opportunities,
        ending_milestone_ids=[EntityId("m_end")],
        clock_definitions=[],
    )


def _make_state(
    current_milestones: set[EntityId] | None = None,
    opportunities: dict[EntityId, OpportunityInstance] | None = None,
    facts: set[EntityId] | None = None,
) -> RuntimeState:
    player = PlayerState(
        id=EntityId("hero"),
        name=DisplayString("Hero"),
        background_id=EntityId("bg-1"),
        stats=_STATS,
        hp=_RES,
        armour=_ZERO,
        mana=_RES,
        mana_regen=2,
        speed=30,
        luck_current=0,
        luck_capacity=3,
    )
    return RuntimeState(
        campaign_id=EntityId("camp"),
        campaign_version="1.0.0",
        campaign_fingerprint="fp",
        save_id=EntityId("save"),
        revision=0,
        difficulty=DefaultDifficulty.NORMAL,
        player=player,
        party=PartyState(protagonist_id=EntityId("hero")),
        location=LocationState(area_id=EntityId("town")),
        plot=PlotState(
            milestones={EntityId("m_start"): MilestoneState.ACTIVE},
            current_milestone_ids=current_milestones or {EntityId("m_start")},
            opportunities=opportunities or {},
        ),
        known_fact_ids=facts or set(),
    )


# ---------------------------------------------------------------------------
# Status Evaluation Tests
# ---------------------------------------------------------------------------


def test_opportunity_status_active() -> None:
    opp = _make_opp_def("opp-1")
    state = _make_state()
    status = evaluate_opportunity_status(opp, None, state)
    assert status == OpportunityStatus.ACTIVE


def test_opportunity_status_locked_parent_not_current() -> None:
    opp = _make_opp_def("opp-1", parent_id="m_future")
    state = _make_state(current_milestones={EntityId("m_start")})
    status = evaluate_opportunity_status(opp, None, state)
    assert status == OpportunityStatus.LOCKED


def test_opportunity_status_locked_preconditions_unmet() -> None:
    opp = _make_opp_def("opp-1", preconditions=["fact:needed_fact"])
    state = _make_state()
    status = evaluate_opportunity_status(opp, None, state)
    assert status == OpportunityStatus.LOCKED


def test_opportunity_status_invalidated_by_expiry() -> None:
    opp = _make_opp_def("opp-1", expiry_conditions=["fact:bridge_destroyed"])
    state = _make_state(facts={EntityId("bridge_destroyed")})
    status = evaluate_opportunity_status(opp, None, state)
    assert status == OpportunityStatus.INVALIDATED


def test_opportunity_status_resolved() -> None:
    opp = _make_opp_def("opp-1")
    instance = OpportunityInstance(opportunity_id=EntityId("opp-1"), is_resolved=True)
    state = _make_state(opportunities={EntityId("opp-1"): instance})
    status = evaluate_opportunity_status(opp, instance, state)
    assert status == OpportunityStatus.RESOLVED


# ---------------------------------------------------------------------------
# Frontier Sync & Bounds Tests
# ---------------------------------------------------------------------------


def test_frontier_sync_target_3_to_7() -> None:
    # 5 opportunities -> all 5 active
    opps = [_make_opp_def(f"opp-{i}") for i in range(1, 6)]
    plot = _make_plot_file(opps)
    state = _make_state()

    new_state, diag = sync_opportunity_frontier(state, plot)
    assert diag.active_count == 5
    assert not diag.is_below_minimum
    assert diag.warning is None
    assert len(new_state.plot.opportunities) == 5


def test_frontier_sync_exceeding_seven_defers_excess() -> None:
    # 9 opportunities -> 7 active, 2 deferred
    opps = [_make_opp_def(f"opp-{i}") for i in range(1, 10)]
    plot = _make_plot_file(opps)
    state = _make_state()

    _new_state, diag = sync_opportunity_frontier(state, plot)
    assert diag.active_count == 7
    assert diag.deferred_count == 2


def test_frontier_sync_below_three_produces_warning() -> None:
    # 2 opportunities -> active_count=2, warning issued
    opps = [_make_opp_def("opp-1"), _make_opp_def("opp-2")]
    plot = _make_plot_file(opps)
    state = _make_state()

    _new_state, diag = sync_opportunity_frontier(state, plot)
    assert diag.active_count == 2
    assert diag.is_below_minimum
    assert diag.warning is not None
    assert "below minimum" in str(diag.warning)


# ---------------------------------------------------------------------------
# Resolution and Transformation Tests
# ---------------------------------------------------------------------------


def test_resolve_opportunity_success() -> None:
    opp = _make_opp_def("opp-1", allowed_outcomes=["success_fact"])
    plot = _make_plot_file([opp])
    state = _make_state()

    new_state, result = resolve_opportunity(
        state, EntityId("opp-1"), EntityId("success_fact"), plot
    )
    assert result.is_resolved
    assert result.outcome_id == EntityId("success_fact")
    assert EntityId("success_fact") in new_state.known_fact_ids
    assert new_state.plot.opportunities[EntityId("opp-1")].is_resolved


def test_resolve_opportunity_invalid_outcome_raises() -> None:
    opp = _make_opp_def("opp-1", allowed_outcomes=["valid_outcome"])
    plot = _make_plot_file([opp])
    state = _make_state()

    with pytest.raises(ValueError, match="not in allowed outcomes"):
        resolve_opportunity(state, EntityId("opp-1"), EntityId("fake_outcome"), plot)


def test_transform_opportunity_tracks_predecessor() -> None:
    state = _make_state()
    new_inst = OpportunityInstance(
        opportunity_id=EntityId("opp-evolved"),
        parent_id=EntityId("m_start"),
    )
    transformed_state = transform_opportunity(state, EntityId("opp-base"), new_inst)

    recorded = transformed_state.plot.opportunities[EntityId("opp-evolved")]
    assert recorded.predecessor_id == EntityId("opp-base")
