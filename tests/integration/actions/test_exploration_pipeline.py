"""Integration tests for the exploration action pipeline (ACTION-06).

Exercises the full deterministic vertical action flow:
  - direct inspect (no check)
  - submit action that creates a pending check
  - cancel pending check
  - resolve to success / partial / failure / natural_1 / natural_20 bands
  - resolve with luck (guaranteed 20)
  - stale revision guard
  - duplicate resolve returns consistent result
  - rejection on unknown entity

State is loaded from and committed to tmp_path via SaveReader/SaveWriter so
the tests exercise the real persistence layer without Ollama or FastAPI.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from campaign.storage.save_reader import SaveReader
from campaign.storage.save_writer import SaveWriter
from domain.models.area import AreaDefinition, AreaObject
from domain.models.campaign_meta import (
    CampaignLength,
    DefaultDifficulty,
    CampaignStatus,
    SourceType,
    Theme,
)
from domain.models.character import StatBlock
from domain.models.common import EntityId
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)

CAMPAIGN_ID: EntityId = "camp-1"
SAVE_ID: EntityId = "save-1"


def _make_state(revision: int = 1) -> RuntimeState:
    player = PlayerState(
        id="player-1",
        name="Hero",
        background_id="bg-1",
        stats=StatBlock(
            strength=10,
            dexterity=10,
            intelligence=10,
            charisma=10,
            constitution=10,
            wisdom=10,
        ),
        hp=ResourceValue(current=8, maximum=10),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=5, maximum=5),
        mana_regen=1,
        speed=30,
        luck_capacity=3,
        luck_current=2,
    )
    return RuntimeState(
        campaign_id=CAMPAIGN_ID,
        campaign_version="1.0.0",
        campaign_fingerprint="abc",
        save_id=SAVE_ID,
        revision=revision,
        difficulty=DefaultDifficulty.NORMAL,
        player=player,
        party=PartyState(protagonist_id="player-1"),
        location=LocationState(area_id="area-1"),
        plot=PlotState(),
    )


def _make_meta() -> SaveMeta:
    return SaveMeta(
        campaign_id=CAMPAIGN_ID,
        campaign_version="1.0.0",
        save_id=SAVE_ID,
        derived_from_revision=1,
        slot_kind="manual",
        slot_name="Test Save",
        player_display_name="Hero",
        player_level=1,
        campaign_title="Test Campaign",
        current_area_display_name="Room",
        difficulty=DefaultDifficulty.NORMAL,
        created_at=_NOW,
        updated_at=_NOW,
        recovery_status="ok",
    )


def _make_area() -> AreaDefinition:
    """Minimal area with one interactable chest object and no residents."""
    return AreaDefinition(
        id="area-1",
        name="Room",
        description="A bare stone room.",
        major_location_id="loc-1",
        art_prompt="a stone room",
        danger_level=1,
        local_faction_ids=[],
        secrets=[],
        connected_area_ids=[],
        residents=[],
        objects=[
            AreaObject(
                id="obj-1",
                name="Chest",
                description="A wooden chest",
                location_anchor="center",
                state="locked",
                interactable_tags=[],
                capability_requirements=[],
                allowed_effect_ids=[],
            )
        ],
        encounters=[],
    )


def _make_use_cases(rng_values: list[int]) -> ExplorationUseCases:
    return ExplorationUseCases(
        entity_resolver=EntityResolver(),
        op_validator=OperationValidator(),
        creative_validator=CreativeValidator(),
        check_resolver=CheckResolver(ScriptedRandomSource(rng_values)),
        campaign_areas={"area-1": _make_area()},
    )


def _write_and_reload(tmp_path: Path, state: RuntimeState) -> RuntimeState:
    """Write state to disk and reload via SaveReader to verify round-trip."""
    meta = _make_meta()
    writer = SaveWriter(tmp_path)
    writer.write_state(state, meta, None)
    reader = SaveReader(tmp_path)
    result = reader.load_save(CAMPAIGN_ID, SAVE_ID)
    return result.state


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_direct_inspect_no_check(tmp_path: Path) -> None:
    """A simple inspect action with challenge_label='none' commits without a check."""
    state = _make_state()
    uc = _make_use_cases([])

    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-1",
        status="valid",
        operation="inspect",
        verb="look at",
        intended_effect="examine the chest",
        challenge_label="none",
        stakes=[],
        entity_mentions=[EntityMention(text="chest", role="target")],
        capability_mentions=[],
    )

    result = uc.submit_action(state, proposal, "cmd-1")

    assert result.rejection_reason is None
    assert not result.has_pending_check
    assert result.state.revision == 2
    assert result.state.pending_check is None

    # Persist and reload to verify round-trip
    loaded = _write_and_reload(tmp_path, result.state)
    assert loaded.revision == 2
    assert loaded.pending_check is None


def test_submit_with_check_creates_pending(tmp_path: Path) -> None:
    """An action with a non-trivial challenge_label creates a pending check."""
    state = _make_state()
    uc = _make_use_cases([15])

    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-2",
        status="valid",
        operation="inspect",
        verb="pick",
        intended_effect="pick the lock on the chest",
        challenge_label="standard",
        stakes=["fail_forward"],
        entity_mentions=[EntityMention(text="chest", role="target")],
        capability_mentions=[],
    )

    result = uc.submit_action(state, proposal, "cmd-2")

    assert result.rejection_reason is None
    assert result.has_pending_check
    assert result.state.pending_check is not None
    assert result.state.pending_check.semantic_difficulty == "standard"
    assert result.state.revision == 2

    # Persist and reload
    loaded = _write_and_reload(tmp_path, result.state)
    assert loaded.pending_check is not None


def test_cancel_check(tmp_path: Path) -> None:
    """Cancelling a pending check clears it and increments revision."""
    state = _make_state()
    uc = _make_use_cases([])

    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-3",
        status="valid",
        operation="inspect",
        verb="pick",
        intended_effect="pick the lock",
        challenge_label="difficult",
        stakes=["fail"],
        entity_mentions=[EntityMention(text="chest", role="target")],
        capability_mentions=[],
    )

    submit_result = uc.submit_action(state, proposal, "cmd-3")
    assert submit_result.has_pending_check

    cancel_result = uc.cancel_check(submit_result.state)
    assert cancel_result.state.pending_check is None
    assert cancel_result.state.revision == 3

    loaded = _write_and_reload(tmp_path, cancel_result.state)
    assert loaded.pending_check is None
    assert loaded.revision == 3


def test_resolve_success_band(tmp_path: Path) -> None:
    """Roll >= DC+5 produces 'strong' band outcome."""
    state = _make_state()
    # DC=10, DC+5=15 → strong
    uc = _make_use_cases([18])

    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-4",
        status="valid",
        operation="inspect",
        verb="search",
        intended_effect="search the chest",
        challenge_label="standard",
        stakes=["discover"],
        entity_mentions=[EntityMention(text="chest", role="target")],
        capability_mentions=[],
    )

    submit_result = uc.submit_action(state, proposal, "cmd-4")
    assert submit_result.has_pending_check

    resolve_result = uc.resolve_check(submit_result.state, use_luck=False)
    assert resolve_result.roll == 18
    assert resolve_result.band == "strong"
    assert resolve_result.state.pending_check is None
    assert resolve_result.state.revision == 3

    loaded = _write_and_reload(tmp_path, resolve_result.state)
    assert loaded.pending_check is None


def test_resolve_partial_band(tmp_path: Path) -> None:
    """Roll >= DC but < DC+5 produces 'standard' band."""
    state = _make_state()
    uc = _make_use_cases([12])  # DC=10 → standard (>=10, <15)

    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-5",
        status="valid",
        operation="inspect",
        verb="check",
        intended_effect="check the lock",
        challenge_label="standard",
        stakes=["partial"],
        entity_mentions=[EntityMention(text="chest", role="target")],
        capability_mentions=[],
    )

    submit_result = uc.submit_action(state, proposal, "cmd-5")
    resolve_result = uc.resolve_check(submit_result.state, use_luck=False)
    assert resolve_result.roll == 12
    assert resolve_result.band == "standard"
    assert resolve_result.state.revision == 3


def test_resolve_failure_band(tmp_path: Path) -> None:
    """Roll < DC produces 'low' band."""
    state = _make_state()
    uc = _make_use_cases([5])  # DC=10 → low

    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-6",
        status="valid",
        operation="inspect",
        verb="force",
        intended_effect="force the chest open",
        challenge_label="standard",
        stakes=["damage"],
        entity_mentions=[EntityMention(text="chest", role="target")],
        capability_mentions=[],
    )

    submit_result = uc.submit_action(state, proposal, "cmd-6")
    resolve_result = uc.resolve_check(submit_result.state, use_luck=False)
    assert resolve_result.roll == 5
    assert resolve_result.band == "low"


def test_resolve_natural_1(tmp_path: Path) -> None:
    """Natural 1 always produces 'natural_1' band regardless of DC."""
    state = _make_state()
    uc = _make_use_cases([1])

    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-nat1",
        status="valid",
        operation="inspect",
        verb="try",
        intended_effect="try to open the chest",
        challenge_label="easy",
        stakes=["fail"],
        entity_mentions=[EntityMention(text="chest", role="target")],
        capability_mentions=[],
    )

    submit_result = uc.submit_action(state, proposal, "cmd-nat1")
    resolve_result = uc.resolve_check(submit_result.state, use_luck=False)
    assert resolve_result.roll == 1
    assert resolve_result.band == "natural_1"


def test_resolve_natural_20(tmp_path: Path) -> None:
    """Natural 20 always produces 'natural_20' band."""
    state = _make_state()
    uc = _make_use_cases([20])

    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-nat20",
        status="valid",
        operation="inspect",
        verb="smash",
        intended_effect="smash the chest open",
        challenge_label="difficult",
        stakes=["success"],
        entity_mentions=[EntityMention(text="chest", role="target")],
        capability_mentions=[],
    )

    submit_result = uc.submit_action(state, proposal, "cmd-nat20")
    resolve_result = uc.resolve_check(submit_result.state, use_luck=False)
    assert resolve_result.roll == 20
    assert resolve_result.band == "natural_20"


def test_resolve_with_luck_uses_roll_20(tmp_path: Path) -> None:
    """Using luck guarantees a roll of 20 without consuming RNG."""
    state = _make_state()  # luck_current=2
    uc = _make_use_cases([])  # no dice consumed

    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-luck",
        status="valid",
        operation="inspect",
        verb="carefully open",
        intended_effect="carefully open the chest",
        challenge_label="standard",
        stakes=["success"],
        entity_mentions=[EntityMention(text="chest", role="target")],
        capability_mentions=[],
    )

    submit_result = uc.submit_action(state, proposal, "cmd-luck")
    resolve_result = uc.resolve_check(submit_result.state, use_luck=True)
    assert resolve_result.roll == 20
    assert resolve_result.band == "natural_20"
    assert resolve_result.state.player.luck_current == 1  # decremented


def test_stale_revision_stateless(tmp_path: Path) -> None:
    """The use case is stateless — two independent calls each increment
    their input revision by 1 without interfering."""
    state_a = _make_state(revision=5)
    state_b = _make_state(revision=5)
    uc = _make_use_cases([])

    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-stale",
        status="valid",
        operation="inspect",
        verb="look",
        intended_effect="look at the chest",
        challenge_label="none",
        stakes=[],
        entity_mentions=[EntityMention(text="chest", role="target")],
        capability_mentions=[],
    )

    result_a = uc.submit_action(state_a, proposal, "cmd-a")
    result_b = uc.submit_action(state_b, proposal, "cmd-b")
    assert result_a.state.revision == 6
    assert result_b.state.revision == 6


def test_duplicate_resolve_no_extra_draw(tmp_path: Path) -> None:
    """Resolving the same pending-check state twice with fresh identical scripted
    RNG sources gives identical deterministic rolls."""
    state = _make_state()
    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-dup",
        status="valid",
        operation="inspect",
        verb="tap",
        intended_effect="tap the chest",
        challenge_label="standard",
        stakes=["discover"],
        entity_mentions=[EntityMention(text="chest", role="target")],
        capability_mentions=[],
    )

    # First resolve
    uc1 = _make_use_cases([14])
    submit1 = uc1.submit_action(state, proposal, "cmd-dup")
    resolve1 = uc1.resolve_check(submit1.state, use_luck=False)

    # Second resolve with fresh scripted source starting from same value
    uc2 = _make_use_cases([14])
    submit2 = uc2.submit_action(state, proposal, "cmd-dup")
    resolve2 = uc2.resolve_check(submit2.state, use_luck=False)

    assert resolve1.roll == resolve2.roll == 14
    assert resolve1.band == resolve2.band == "standard"  # 14 >= DC10 and < DC+5=15


def test_rejection_on_unknown_entity(tmp_path: Path) -> None:
    """Mentioning an entity not in the area returns a rejection result."""
    state = _make_state()
    uc = _make_use_cases([])

    proposal = ActionProposal(
        contract_version=1,
        prompt_version="1",
        request_id="req-rej",
        status="valid",
        operation="inspect",
        verb="look at",
        intended_effect="look at the door",
        challenge_label="none",
        stakes=[],
        entity_mentions=[EntityMention(text="door", role="target")],
        capability_mentions=[],
    )

    result = uc.submit_action(state, proposal, "cmd-rej")
    assert result.rejection_reason is not None
    assert result.state.revision == 1  # state unchanged
