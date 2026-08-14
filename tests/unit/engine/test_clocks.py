"""Tests for event-driven clocks and paired challenges (PLOT-04)."""

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.common import DisplayString, EntityId
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot import ClockDefinition, ClockVisibility
from domain.models.plot_state import ClockState, PlotState
from domain.models.runtime_common import ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.world_state import LocationState
from engine.plot.clocks import (
    advance_clock,
    evaluate_paired_challenge,
    initialize_clock,
    process_event_clocks,
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


def _make_clock_def(
    clock_id: str = "threat_clock",
    maximum: int = 4,
    triggers: list[str] | None = None,
    effects: list[str] | None = None,
) -> ClockDefinition:
    return ClockDefinition(
        id=EntityId(clock_id),
        name=DisplayString(clock_id.title()),
        maximum=maximum,
        visibility=ClockVisibility.PUBLIC,
        trigger_event_types=[
            DisplayString(t) for t in (triggers or ["patrol_alarm", "stealth_failure"])
        ],
        completion_effect_ids=[EntityId(e) for e in (effects or ["reinforcements_arrived"])],
    )


def _make_state(
    clocks: dict[EntityId, ClockState] | None = None,
    revision: int = 0,
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
        revision=revision,
        difficulty=DefaultDifficulty.NORMAL,
        player=player,
        party=PartyState(protagonist_id=EntityId("hero")),
        location=LocationState(area_id=EntityId("town")),
        plot=PlotState(),
        clocks=clocks or {},
    )


# ---------------------------------------------------------------------------
# Clock Advancement Tests
# ---------------------------------------------------------------------------


def test_initialize_clock() -> None:
    clock_def = _make_clock_def("alarm_clock", maximum=6)
    state = _make_state()

    new_state = initialize_clock(clock_def, state)
    assert EntityId("alarm_clock") in new_state.clocks
    assert new_state.clocks[EntityId("alarm_clock")].current == 0
    assert new_state.clocks[EntityId("alarm_clock")].maximum == 6
    assert not new_state.clocks[EntityId("alarm_clock")].completed


def test_advance_clock_increment() -> None:
    clock_def = _make_clock_def("alarm_clock", maximum=4)
    state = _make_state()

    s1, res1 = advance_clock(state, EntityId("alarm_clock"), clock_def, amount=1)
    assert res1.previous_value == 0
    assert res1.new_value == 1
    assert not res1.just_completed

    _s2, res2 = advance_clock(s1, EntityId("alarm_clock"), clock_def, amount=2)
    assert res2.previous_value == 1
    assert res2.new_value == 3
    assert not res2.just_completed


def test_advance_clock_completion_and_effects() -> None:
    clock_def = _make_clock_def("alarm_clock", maximum=4, effects=["guards_alerted"])
    state = _make_state(
        clocks={
            EntityId("alarm_clock"): ClockState(
                clock_id=EntityId("alarm_clock"),
                current=3,
                maximum=4,
                completed=False,
                last_advancement_revision=0,
            )
        }
    )

    s1, res1 = advance_clock(state, EntityId("alarm_clock"), clock_def, amount=1)
    assert res1.new_value == 4
    assert res1.just_completed
    assert res1.completion_effect_ids == [EntityId("guards_alerted")]
    assert EntityId("guards_alerted") in s1.known_fact_ids
    assert s1.clocks[EntityId("alarm_clock")].completed

    # Subsequent advancement while completed caps at maximum and does NOT re-apply effects
    _s2, res2 = advance_clock(s1, EntityId("alarm_clock"), clock_def, amount=2)
    assert res2.new_value == 4
    assert not res2.just_completed
    assert not res2.completion_effect_ids


def test_advance_clock_invalid_amount_raises() -> None:
    clock_def = _make_clock_def()
    state = _make_state()

    with pytest.raises(ValueError, match="amount must be >= 1"):
        advance_clock(state, EntityId("threat_clock"), clock_def, amount=0)


# ---------------------------------------------------------------------------
# Event Processing & Non-Trigger Ignored Events
# ---------------------------------------------------------------------------


def test_process_event_matching_triggers() -> None:
    c1 = _make_clock_def("clk_1", maximum=4, triggers=["patrol_alarm"])
    c2 = _make_clock_def("clk_2", maximum=4, triggers=["stealth_failure"])
    state = _make_state()

    new_state, results = process_event_clocks(state, "patrol_alarm", [c1, c2])
    assert len(results) == 1
    assert results[0].clock_id == EntityId("clk_1")
    assert new_state.clocks[EntityId("clk_1")].current == 1
    assert EntityId("clk_2") not in new_state.clocks


def test_process_event_ignores_reading_and_inventory() -> None:
    c1 = _make_clock_def("clk_1", triggers=["inventory_opened", "read_book"])
    state = _make_state()

    s1, res1 = process_event_clocks(state, "inventory_opened", [c1])
    assert len(res1) == 0

    _s2, res2 = process_event_clocks(s1, "read_note", [c1])
    assert len(res2) == 0


# ---------------------------------------------------------------------------
# Paired Challenge Clocks Tests
# ---------------------------------------------------------------------------


def test_evaluate_paired_challenge_unresolved() -> None:
    s_id = EntityId("hack_success")
    c_id = EntityId("hack_complication")
    state = _make_state(
        clocks={
            s_id: ClockState(
                clock_id=s_id,
                current=2,
                maximum=4,
                completed=False,
                last_advancement_revision=0,
            ),
            c_id: ClockState(
                clock_id=c_id,
                current=1,
                maximum=4,
                completed=False,
                last_advancement_revision=0,
            ),
        }
    )

    result = evaluate_paired_challenge(state, s_id, c_id)
    assert not result.is_resolved
    assert result.winner == "none"


def test_evaluate_paired_challenge_success_wins() -> None:
    s_id = EntityId("hack_success")
    c_id = EntityId("hack_complication")
    state = _make_state(
        clocks={
            s_id: ClockState(
                clock_id=s_id,
                current=4,
                maximum=4,
                completed=True,
                last_advancement_revision=0,
            ),
            c_id: ClockState(
                clock_id=c_id,
                current=2,
                maximum=4,
                completed=False,
                last_advancement_revision=0,
            ),
        }
    )

    result = evaluate_paired_challenge(state, s_id, c_id)
    assert result.is_resolved
    assert result.winner == "success"


def test_evaluate_paired_challenge_complication_wins() -> None:
    s_id = EntityId("hack_success")
    c_id = EntityId("hack_complication")
    state = _make_state(
        clocks={
            s_id: ClockState(
                clock_id=s_id,
                current=2,
                maximum=4,
                completed=False,
                last_advancement_revision=0,
            ),
            c_id: ClockState(
                clock_id=c_id,
                current=4,
                maximum=4,
                completed=True,
                last_advancement_revision=0,
            ),
        }
    )

    result = evaluate_paired_challenge(state, s_id, c_id)
    assert result.is_resolved
    assert result.winner == "complication"


def test_evaluate_paired_challenge_both_completed_order_resolution() -> None:
    s_id = EntityId("hack_success")
    c_id = EntityId("hack_complication")
    # Success completed at revision 2, complication at revision 5 -> success wins
    state = _make_state(
        clocks={
            s_id: ClockState(
                clock_id=s_id,
                current=4,
                maximum=4,
                completed=True,
                last_advancement_revision=2,
            ),
            c_id: ClockState(
                clock_id=c_id,
                current=4,
                maximum=4,
                completed=True,
                last_advancement_revision=5,
            ),
        }
    )

    result = evaluate_paired_challenge(state, s_id, c_id)
    assert result.is_resolved
    assert result.winner == "success"


# ---------------------------------------------------------------------------
# Architecture Policy: No system clock imports
# ---------------------------------------------------------------------------


def test_no_system_clock_imports() -> None:
    """Validate that engine.plot modules have NO datetime/time/system clock imports."""
    import inspect

    import engine.plot.clocks as clocks_mod
    import engine.plot.milestones as milestones_mod
    import engine.plot.opportunities as opps_mod
    import engine.plot.predicates as preds_mod

    for mod in (clocks_mod, milestones_mod, opps_mod, preds_mod):
        source = inspect.getsource(mod)
        assert "datetime.now" not in source
        assert "time.time" not in source
        assert "import time\n" not in source
