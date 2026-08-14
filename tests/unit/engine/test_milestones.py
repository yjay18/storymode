"""Tests for milestone state transitions, predicates, and spine progression (PLOT-01)."""

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.common import DisplayString, EntityId
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot import MilestoneDefinition, PlotFile
from domain.models.plot_state import ClockState, MilestoneState, PlotState
from domain.models.runtime_common import InventoryEntry, ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.world_state import LocationState
from engine.plot.milestones import (
    activate_milestone,
    fail_milestone,
    initialize_plot_state,
    resolve_milestone,
)
from engine.plot.predicates import evaluate_all_predicates, evaluate_predicate

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


def _make_state(
    milestones: dict[EntityId, MilestoneState] | None = None,
    current_milestones: set[EntityId] | None = None,
    facts: set[EntityId] | None = None,
    flags: dict[EntityId, bool | int | str] | None = None,
    inventory: list[tuple[str, int]] | None = None,
    area_id: str = "town_square",
    level: int = 1,
    clocks: dict[EntityId, ClockState] | None = None,
) -> RuntimeState:
    inv_entries = [
        InventoryEntry(item_id=EntityId(i_id), quantity=qty) for i_id, qty in (inventory or [])
    ]
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
        level=level,
        inventory=inv_entries,
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
        location=LocationState(area_id=EntityId(area_id)),
        plot=PlotState(
            milestones=milestones or {},
            current_milestone_ids=current_milestones or set(),
        ),
        known_fact_ids=facts or set(),
        world_flags=flags or {},
        clocks=clocks or {},
    )


def _make_milestone(
    m_id: str,
    next_ids: list[str] | None = None,
    preconditions: list[str] | None = None,
    required_outcomes: list[str] | None = None,
    forbidden_changes: list[str] | None = None,
    cycle_allowed: bool = False,
) -> MilestoneDefinition:
    return MilestoneDefinition(
        id=EntityId(m_id),
        canonical_truth=DisplayString("Canonical truth"),
        narrative_purpose=DisplayString("Purpose"),
        required_outcome_ids=[EntityId(o) for o in (required_outcomes or [f"outcome_{m_id}"])],
        allowed_approach_tags=[DisplayString("approach")],
        forbidden_changes=[DisplayString(f) for f in (forbidden_changes or [])],
        preconditions=[DisplayString(p) for p in (preconditions or [])],
        valid_next_milestone_ids=[EntityId(n) for n in (next_ids or [])],
        difficulty_band=DisplayString("standard"),
        pacing_weight=50,
        cycle_allowed=cycle_allowed,
    )


def _make_plot_file(
    milestones: list[MilestoneDefinition],
    starts: list[str] | None = None,
    endings: list[str] | None = None,
) -> PlotFile:
    return PlotFile(
        campaign_id=EntityId("camp"),
        campaign_version="1.0.0",
        start_milestone_ids=[EntityId(s) for s in (starts or ["m_start"])],
        milestones=milestones,
        authored_opportunities=[],
        ending_milestone_ids=[EntityId(e) for e in (endings or ["m_end"])],
        clock_definitions=[],
    )


# ---------------------------------------------------------------------------
# Predicate Evaluator Tests
# ---------------------------------------------------------------------------


def test_predicates_facts() -> None:
    state = _make_state(facts={EntityId("fact_discovered")})
    assert evaluate_predicate("fact:fact_discovered", state)
    assert not evaluate_predicate("fact:unknown_fact", state)
    assert evaluate_predicate("!fact:unknown_fact", state)
    assert not evaluate_predicate("!fact:fact_discovered", state)


def test_predicates_flags() -> None:
    state = _make_state(flags={EntityId("flag_bool"): True, EntityId("flag_count"): 5})
    assert evaluate_predicate("flag:flag_bool", state)
    assert evaluate_predicate("flag:flag_count=5", state)
    assert evaluate_predicate("flag:flag_count>=3", state)
    assert not evaluate_predicate("flag:flag_count>=10", state)
    assert evaluate_predicate("!flag:missing_flag", state)


def test_predicates_milestones() -> None:
    state = _make_state(
        milestones={
            EntityId("m_one"): MilestoneState.RESOLVED,
            EntityId("m_two"): MilestoneState.ACTIVE,
            EntityId("m_three"): MilestoneState.LOCKED,
        }
    )
    assert evaluate_predicate("milestone:m_one", state)
    assert evaluate_predicate("milestone:m_one=resolved", state)
    assert evaluate_predicate("milestone:m_two=active", state)
    assert evaluate_predicate("milestone:m_three=locked", state)
    assert evaluate_predicate("milestone:untracked_m=locked", state)
    assert not evaluate_predicate("milestone:m_two=resolved", state)


def test_predicates_level_and_location() -> None:
    state = _make_state(level=3, area_id="castle_courtyard")
    assert evaluate_predicate("min_level:2", state)
    assert evaluate_predicate("level:3", state)
    assert not evaluate_predicate("min_level:5", state)
    assert evaluate_predicate("location:castle_courtyard", state)
    assert not evaluate_predicate("area:dark_dungeon", state)


def test_predicates_clocks_and_items() -> None:
    clock = ClockState(
        clock_id=EntityId("threat_clock"),
        current=4,
        maximum=6,
        completed=False,
        last_advancement_revision=0,
    )
    state = _make_state(inventory=[("gold_key", 2)], clocks={EntityId("threat_clock"): clock})
    assert evaluate_predicate("clock:threat_clock>=3", state)
    assert not evaluate_predicate("clock:threat_clock>=5", state)
    assert not evaluate_predicate("clock:threat_clock=completed", state)
    assert evaluate_predicate("item:gold_key", state)
    assert evaluate_predicate("item:gold_key>=2", state)
    assert not evaluate_predicate("item:gold_key>=5", state)


def test_evaluate_all_predicates() -> None:
    state = _make_state(facts={EntityId("fact_1")}, level=3)
    assert evaluate_all_predicates(["fact:fact_1", "min_level:2"], state)
    assert not evaluate_all_predicates(["fact:fact_1", "min_level:5"], state)


# ---------------------------------------------------------------------------
# Milestone State Transitions Tests
# ---------------------------------------------------------------------------


def test_initialize_plot_state() -> None:
    m1 = _make_milestone("m_start", next_ids=["m_mid"])
    m2 = _make_milestone("m_mid", next_ids=["m_end"])
    m3 = _make_milestone("m_end")
    plot = _make_plot_file([m1, m2, m3])
    state = _make_state()

    init_state = initialize_plot_state(plot, state)

    assert init_state.plot.milestones[EntityId("m_start")] == MilestoneState.AVAILABLE
    assert init_state.plot.milestones[EntityId("m_mid")] == MilestoneState.LOCKED
    assert init_state.plot.milestones[EntityId("m_end")] == MilestoneState.LOCKED


def test_activate_milestone_success() -> None:
    m1 = _make_milestone("m_start")
    plot = _make_plot_file([m1])
    state = _make_state(milestones={EntityId("m_start"): MilestoneState.AVAILABLE})

    active_state = activate_milestone(state, EntityId("m_start"), plot)

    assert active_state.plot.milestones[EntityId("m_start")] == MilestoneState.ACTIVE
    assert EntityId("m_start") in active_state.plot.current_milestone_ids


def test_activate_milestone_preconditions_unmet_raises() -> None:
    m1 = _make_milestone("m_start", preconditions=["fact:secret_knowledge"])
    plot = _make_plot_file([m1])
    state = _make_state(milestones={EntityId("m_start"): MilestoneState.LOCKED})

    with pytest.raises(ValueError, match="preconditions not met"):
        activate_milestone(state, EntityId("m_start"), plot)


def test_resolve_milestone_branching_routes() -> None:
    """Resolving a milestone unlocks all valid next milestones whose preconditions are met."""
    m_root = _make_milestone("m_root", next_ids=["m_left", "m_right"])
    m_left = _make_milestone("m_left", next_ids=["m_end"])
    m_right = _make_milestone("m_right", next_ids=["m_end"], preconditions=["flag:has_key"])
    m_end = _make_milestone("m_end")
    plot = _make_plot_file([m_root, m_left, m_right, m_end], starts=["m_root"])

    state = _make_state(
        milestones={
            EntityId("m_root"): MilestoneState.ACTIVE,
            EntityId("m_left"): MilestoneState.LOCKED,
            EntityId("m_right"): MilestoneState.LOCKED,
            EntityId("m_end"): MilestoneState.LOCKED,
        },
        current_milestones={EntityId("m_root")},
    )

    new_state, result = resolve_milestone(
        state, EntityId("m_root"), EntityId("outcome_m_root"), plot
    )

    # Left is unlocked, right is still locked because flag:has_key is unmet
    assert result.milestone_id == EntityId("m_root")
    assert result.unlocked_next_milestone_ids == [EntityId("m_left")]
    assert new_state.plot.milestones[EntityId("m_root")] == MilestoneState.RESOLVED
    assert new_state.plot.milestones[EntityId("m_left")] == MilestoneState.AVAILABLE
    assert new_state.plot.milestones[EntityId("m_right")] == MilestoneState.LOCKED
    assert EntityId("outcome_m_root") in new_state.known_fact_ids


def test_resolve_ending_milestone() -> None:
    m_end = _make_milestone("m_end", required_outcomes=["victory_outcome"])
    plot = _make_plot_file([m_end], starts=["m_end"], endings=["m_end"])
    state = _make_state(
        milestones={EntityId("m_end"): MilestoneState.ACTIVE},
        current_milestones={EntityId("m_end")},
    )

    new_state, result = resolve_milestone(
        state, EntityId("m_end"), EntityId("victory_outcome"), plot
    )

    assert result.is_campaign_ending
    assert new_state.plot.ending_state is not None
    assert "victory_outcome" in str(new_state.plot.ending_state)


def test_resolve_invalid_outcome_raises() -> None:
    m1 = _make_milestone("m_start", required_outcomes=["good_end", "bad_end"])
    plot = _make_plot_file([m1])
    state = _make_state(milestones={EntityId("m_start"): MilestoneState.ACTIVE})

    with pytest.raises(ValueError, match="not in required outcomes"):
        resolve_milestone(state, EntityId("m_start"), EntityId("made_up_outcome"), plot)


def test_resolve_forbidden_change_raises() -> None:
    m1 = _make_milestone(
        "m_start",
        required_outcomes=["forbidden_act"],
        forbidden_changes=["forbidden_act"],
    )
    plot = _make_plot_file([m1])
    state = _make_state(milestones={EntityId("m_start"): MilestoneState.ACTIVE})

    with pytest.raises(ValueError, match="violates forbidden change"):
        resolve_milestone(state, EntityId("m_start"), EntityId("forbidden_act"), plot)


def test_fail_milestone() -> None:
    m1 = _make_milestone("m_start")
    plot = _make_plot_file([m1])
    state = _make_state(
        milestones={EntityId("m_start"): MilestoneState.ACTIVE},
        current_milestones={EntityId("m_start")},
    )

    new_state = fail_milestone(state, EntityId("m_start"), plot)

    assert new_state.plot.milestones[EntityId("m_start")] == MilestoneState.FAILED
    assert EntityId("m_start") not in new_state.plot.current_milestone_ids
