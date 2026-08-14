"""Tests for exploration use cases (unit tests; deprecated path).

NOTE: ACTION-06 places the canonical use cases in engine.actions.use_cases.
This file tests the older use_cases.exploration module for regression coverage.
"""

import datetime
from pathlib import Path

import pytest

from campaign.storage.save_writer import SaveWriter
from domain.models.area import AreaDefinition, AreaObject
from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.save_meta import SaveMeta
from domain.models.world_state import LocationState
from engine.actions.creative import CreativeValidator
from engine.actions.operations import OperationValidator
from engine.actions.resolution import CheckResolver
from engine.actions.resolver import EntityResolver
from engine.actions.use_cases import ExplorationUseCases
from engine.dice.testing import ScriptedRandomSource
from llm.contracts.action import ActionProposal, EntityMention

_NOW = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)


@pytest.fixture
def base_state() -> RuntimeState:
    player = PlayerState(
        id="player-1",
        name="Hero",
        background_id="bg-1",
        stats=StatBlock(
            strength=10, dexterity=10, intelligence=10, charisma=10, constitution=10, wisdom=10
        ),
        hp=ResourceValue(current=5, maximum=10),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=5, maximum=5),
        mana_regen=1,
        speed=30,
        luck_capacity=3,
        luck_current=2,
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
def campaign_meta() -> SaveMeta:
    return SaveMeta(
        campaign_id="camp-1",
        campaign_version="1.0.0",
        save_id="save-1",
        derived_from_revision=1,
        slot_kind="manual",
        slot_name="Test",
        player_display_name="Hero",
        player_level=1,
        campaign_title="Test Campaign",
        current_area_display_name="Room",
        difficulty=DefaultDifficulty.NORMAL,
        created_at=_NOW,
        updated_at=_NOW,
        recovery_status="ok",
    )


@pytest.fixture
def setup_use_cases(
    tmp_path: Path, base_state: RuntimeState, campaign_meta: SaveMeta
) -> tuple[ExplorationUseCases, RuntimeState]:
    writer = SaveWriter(tmp_path)
    writer.write_state(base_state, campaign_meta, None)

    area = AreaDefinition(
        id="area-1",
        name="Room",
        description="A bare room.",
        major_location_id="loc-1",
        art_prompt="art",
        danger_level=1,
        local_faction_ids=[],
        secrets=[],
        connected_area_ids=[],
        residents=[],
        objects=[
            AreaObject(
                id="obj-1",
                name="Chest",
                description="A chest",
                location_anchor="Center",
                state="locked",
                interactable_tags=[],
                capability_requirements=[],
                allowed_effect_ids=[],
            )
        ],
        encounters=[],
    )

    uc = ExplorationUseCases(
        entity_resolver=EntityResolver(),
        op_validator=OperationValidator(),
        creative_validator=CreativeValidator(),
        check_resolver=CheckResolver(ScriptedRandomSource([15])),
        campaign_areas={"area-1": area},
    )
    return uc, base_state


def test_submit_action(
    setup_use_cases: tuple[ExplorationUseCases, RuntimeState],
) -> None:
    uc, state = setup_use_cases
    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-1",
        status="valid",
        operation="inspect",
        verb="look",
        intended_effect="look at the chest",
        challenge_label="none",
        stakes=[],
        entity_mentions=[EntityMention(text="chest", role="target")],
        capability_mentions=[],
    )

    result = uc.submit_action(state, proposal, "cmd-1")
    assert result.rejection_reason is None
    assert result.state.revision == 2
    assert result.state.pending_check is None


def test_submit_action_with_check(
    setup_use_cases: tuple[ExplorationUseCases, RuntimeState],
) -> None:
    uc, state = setup_use_cases
    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-1",
        status="valid",
        operation="inspect",
        verb="pick",
        intended_effect="pick the lock",
        challenge_label="standard",
        stakes=["fail"],
        entity_mentions=[EntityMention(text="chest", role="target")],
        capability_mentions=[],
    )

    result = uc.submit_action(state, proposal, "cmd-2")
    assert result.rejection_reason is None
    assert result.state.revision == 2
    assert result.state.pending_check is not None
    assert result.state.pending_check.semantic_difficulty == "standard"


def test_resolve_check(
    setup_use_cases: tuple[ExplorationUseCases, RuntimeState],
) -> None:
    uc, state = setup_use_cases
    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-1",
        status="valid",
        operation="inspect",
        verb="pick",
        intended_effect="pick the lock",
        challenge_label="standard",
        stakes=["fail"],
        entity_mentions=[EntityMention(text="chest", role="target")],
        capability_mentions=[],
    )

    submit_result = uc.submit_action(state, proposal, "cmd-2")
    assert submit_result.has_pending_check

    resolve_result = uc.resolve_check(submit_result.state, use_luck=False)
    assert resolve_result.state.revision == 3
    assert resolve_result.state.pending_check is None
    assert resolve_result.roll == 15
    assert resolve_result.band == "strong"
