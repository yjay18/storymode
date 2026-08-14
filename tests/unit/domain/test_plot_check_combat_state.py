"""Tests for plot, pending check, and combat runtime models."""

import pytest

from domain.models.check_state import CheckOutcomes, PendingCheck
from domain.models.combat_state import CombatParticipant, CombatPhase, CombatState, ParticipantSide
from domain.models.plot_state import ClockState, MilestoneState, OpportunityInstance, PlotState
from domain.models.runtime_common import ResourceValue


def test_plot_state_enums() -> None:
    # Validate enum choices
    ms = MilestoneState("active")
    assert ms == MilestoneState.ACTIVE

    op = OpportunityInstance(opportunity_id="op-1", is_resolved=True)
    assert op.opportunity_id == "op-1"

    plot = PlotState(
        milestones={"ms-1": MilestoneState.ACTIVE},
        opportunities={"op-1": op},
        current_milestone_ids={"ms-1"},
    )
    assert plot.milestones["ms-1"] == MilestoneState.ACTIVE


def test_clock_state_bounds() -> None:
    # Valid
    c = ClockState(clock_id="c-1", current=2, maximum=4, last_advancement_revision=10)
    assert c.current == 2

    # Validation errors
    with pytest.raises(ValueError):
        ClockState(clock_id="c-2", current=-1, maximum=4, last_advancement_revision=10)


def test_pending_check_arithmetic() -> None:
    outcomes = CheckOutcomes(natural_1=[], low=[], standard=[], strong=[], natural_20=[])

    # Valid arithmetic
    c = PendingCheck(
        check_id="chk-1",
        source_command_id="cmd-1",
        source_revision=1,
        original_input="attack",
        resolved_operation="attack",
        actor_id="hero",
        semantic_difficulty="Standard",
        stakes="High",
        allowed_outcomes=outcomes,
        base_dc=12,
        difficulty_adjustment=-2,
        final_dc=10,
    )
    assert c.final_dc == 10

    # Invalid arithmetic
    with pytest.raises(ValueError, match="Arithmetic mismatch"):
        PendingCheck(
            check_id="chk-2",
            source_command_id="cmd-1",
            source_revision=1,
            original_input="attack",
            resolved_operation="attack",
            actor_id="hero",
            semantic_difficulty="Standard",
            stakes="High",
            allowed_outcomes=outcomes,
            base_dc=12,
            difficulty_adjustment=-2,
            final_dc=12,  # Should be 10
        )


def test_combat_state_invariants() -> None:
    p1 = CombatParticipant(
        hp=ResourceValue(current=10, maximum=10),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=0, maximum=5),
        side=ParticipantSide.PARTY,
    )
    p2 = CombatParticipant(
        hp=ResourceValue(current=5, maximum=5),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=0, maximum=5),
        side=ParticipantSide.ENEMY,
    )

    # Valid
    c = CombatState(
        encounter_id="enc-1",
        phase=CombatPhase.ACTIVE,
        order=["hero", "goblin"],
        current_index=0,
        participants={"hero": p1, "goblin": p2},
    )
    assert c.phase == CombatPhase.ACTIVE

    # Terminal phase rejection
    with pytest.raises(ValueError, match="cannot be persisted in terminal phase: victory"):
        CombatState(
            encounter_id="enc-1",
            phase=CombatPhase.VICTORY,
            order=["hero"],
            participants={"hero": p1},
        )

    # Duplicate order
    with pytest.raises(ValueError, match="order contains duplicates"):
        CombatState(
            encounter_id="enc-1",
            phase=CombatPhase.ACTIVE,
            order=["hero", "hero"],
            participants={"hero": p1},
        )

    # Current index bounds
    with pytest.raises(ValueError, match="out of bounds"):
        CombatState(
            encounter_id="enc-1",
            phase=CombatPhase.ACTIVE,
            order=["hero", "goblin"],
            current_index=2,  # Size is 2, index 2 is OOB
            participants={"hero": p1, "goblin": p2},
        )

    # Unknown actor in order
    with pytest.raises(ValueError, match="actor goblin in order is not in participants dict"):
        CombatState(
            encounter_id="enc-1",
            phase=CombatPhase.ACTIVE,
            order=["hero", "goblin"],
            participants={"hero": p1},
        )
