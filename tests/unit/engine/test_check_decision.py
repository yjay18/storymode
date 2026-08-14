"""Tests for check necessity and pending checks."""

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.check_state import CheckOutcomes
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.world_state import LocationState
from engine.actions.checks import build_pending_check, cancel_pending_check, decide_check_necessity
from llm.contracts.action import ActionProposal


@pytest.fixture
def mock_state() -> RuntimeState:
    player = PlayerState(
        id="player-1",
        name="Hero",
        background_id="bg-1",
        stats=StatBlock(
            strength=10, dexterity=10, intelligence=10, charisma=10, constitution=10, wisdom=10
        ),
        hp=ResourceValue(current=10, maximum=10),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=5, maximum=5),
        mana_regen=1,
        speed=30,
        luck_capacity=3,
    )
    return RuntimeState(
        campaign_id="camp-1",
        campaign_version="1.0.0",
        campaign_fingerprint="abc",
        save_id="save-1",
        revision=1,
        difficulty=DefaultDifficulty.NORMAL,
        player=player,
        party=PartyState(protagonist_id="player-1"),
        location=LocationState(area_id="area-1"),
        plot=PlotState(),
    )


@pytest.fixture
def empty_outcomes() -> CheckOutcomes:
    return CheckOutcomes(natural_1=[], low=[], standard=[], strong=[], natural_20=[])


def test_decide_check_necessity() -> None:
    no_check = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="r1",
        status="valid",
        operation="inspect",
        verb="look",
        intended_effect="look",
        challenge_label="none",
    )
    needs_check = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="r1",
        status="valid",
        operation="investigate",
        verb="look",
        intended_effect="look deeply",
        challenge_label="standard",
    )

    assert decide_check_necessity(no_check) is False
    assert decide_check_necessity(needs_check) is True


def test_build_pending_check(mock_state: RuntimeState, empty_outcomes: CheckOutcomes) -> None:
    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="r1",
        status="valid",
        operation="investigate",
        verb="lift",
        intended_effect="Lift the boulder",
        challenge_label="difficult",
        stakes=["Might drop it", "Noise"],
    )

    check = build_pending_check(
        command_id="cmd-1",
        state=mock_state,
        proposal=proposal,
        base_dc=15,
        difficulty_adjustment=2,
        actor_id="player-1",
        target_ids=["obj-boulder"],
        outcomes=empty_outcomes,
    )

    assert check.source_command_id == "cmd-1"
    assert check.source_revision == mock_state.revision
    assert check.actor_id == "player-1"
    assert check.target_ids == ["obj-boulder"]
    assert check.semantic_difficulty == "difficult"
    assert check.base_dc == 15
    assert check.difficulty_adjustment == 2
    assert check.final_dc == 17
    assert check.stakes == "Might drop it | Noise"


def test_cancel_pending_check(mock_state: RuntimeState, empty_outcomes: CheckOutcomes) -> None:
    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="r1",
        status="valid",
        operation="investigate",
        verb="lift",
        intended_effect="Lift the boulder",
        challenge_label="difficult",
        stakes=["Might drop it", "Noise"],
    )

    check = build_pending_check(
        command_id="cmd-1",
        state=mock_state,
        proposal=proposal,
        base_dc=15,
        difficulty_adjustment=2,
        actor_id="player-1",
        target_ids=["obj-boulder"],
        outcomes=empty_outcomes,
    )

    state_with_check = mock_state.model_copy(update={"pending_check": check})
    assert state_with_check.pending_check is not None

    # Cancel it
    state_without_check = cancel_pending_check(state_with_check)
    assert state_without_check.pending_check is None

    # Cannot cancel if None
    with pytest.raises(ValueError, match="No active pending check"):
        cancel_pending_check(state_without_check)
