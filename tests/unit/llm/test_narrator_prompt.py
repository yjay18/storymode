"""Unit tests for narrator context packet builder and prompt renderer (LLM-06)."""

from pathlib import Path

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.common import DisplayString
from domain.models.pack import CampaignPack
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import ResourceValue
from domain.models.runtime_state import CommandReceipt, RuntimeState
from domain.models.world_state import LocationState
from engine.campaign import load_campaign
from llm.prompts.narrator_v1 import NARRATOR_PROMPT_VERSION, render_narrator_prompt
from llm.retrieval.narrator_context import (
    CommittedRollView,
    NarratorContextOverflowError,
    build_narrator_context_packet,
)


@pytest.fixture
def minimal_pack() -> CampaignPack:
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "campaigns" / "valid-minimal"
    pack, _ = load_campaign(fixture_path)
    assert pack is not None
    return pack


@pytest.fixture
def sample_state() -> RuntimeState:
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
        hp=ResourceValue(current=10, maximum=10),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=5, maximum=5),
        mana_regen=1,
        speed=30,
        luck_capacity=3,
    )
    return RuntimeState(
        schema_version=1,
        save_id="save-1",
        campaign_id="minimal-campaign",
        campaign_version="1.0.0",
        campaign_fingerprint="fp-123",
        difficulty=DefaultDifficulty.NORMAL,
        revision=1,
        player=player,
        party=PartyState(protagonist_id="player-1"),
        location=LocationState(area_id="area-1", discovered_area_ids={"area-1"}),
        plot=PlotState(),
        known_fact_ids={"fact-1"},
    )


@pytest.fixture
def sample_receipt() -> CommandReceipt:
    return CommandReceipt(
        command_id="cmd-investigate-1",
        canonical_request_hash="hash123",
        committed_revision=2,
        result_kind=DisplayString("investigate"),
        safe_result_summary=DisplayString(
            "Found an ancient iron key hidden under the loose flagstone."
        ),
    )


def test_build_narrator_context_packet_success(
    sample_state: RuntimeState, minimal_pack: CampaignPack, sample_receipt: CommandReceipt
) -> None:
    roll_view = CommittedRollView(
        natural_roll=16,
        modifier=2,
        total=18,
        target_dc=15,
        outcome="success",
    )
    recent_memories = [
        "Entered the dusty tavern.",
        "Spoke with the tavern keeper.",
        "Found a secret passage behind the hearth.",
    ]

    packet = build_narrator_context_packet(
        request_id="req-narr-1",
        state=sample_state,
        pack=minimal_pack,
        receipt=sample_receipt,
        roll_view=roll_view,
        raw_recent_memories=recent_memories,
    )

    assert packet.schema_version == 1
    assert packet.request_id == "req-narr-1"
    assert packet.committed_revision == 2
    assert "ancient iron key" in packet.safe_result_summary
    assert packet.roll_display is not None
    assert packet.roll_display.total == 18
    assert len(packet.recent_memories) == 3
    assert len(packet.present_speakers) >= 1
    assert packet.present_speakers[0].id == "player-1"
    assert len(packet.forbidden_claims) > 0


def test_render_narrator_prompt_structure(
    sample_state: RuntimeState, minimal_pack: CampaignPack, sample_receipt: CommandReceipt
) -> None:
    packet = build_narrator_context_packet(
        request_id="req-narr-2",
        state=sample_state,
        pack=minimal_pack,
        receipt=sample_receipt,
    )

    messages = render_narrator_prompt(packet)
    assert len(messages) == 2

    sys_msg, user_msg = messages[0], messages[1]
    assert sys_msg.role == "system"
    assert user_msg.role == "user"

    assert NARRATOR_PROMPT_VERSION in sys_msg.content
    assert "Forbidden Mechanical Claims" in sys_msg.content

    assert "<NARRATOR_CONTEXT>" in user_msg.content
    assert "</NARRATOR_CONTEXT>" in user_msg.content
    assert "<COMMITTED_EVENT>" in user_msg.content
    assert "</COMMITTED_EVENT>" in user_msg.content
    assert "Found an ancient iron key" in user_msg.content


def test_narrator_context_pruning_and_overflow(
    sample_state: RuntimeState, minimal_pack: CampaignPack, sample_receipt: CommandReceipt
) -> None:
    # Test that extremely tight budget raises overflow
    with pytest.raises(NarratorContextOverflowError, match="exceeds budget"):
        build_narrator_context_packet(
            request_id="req-overflow",
            state=sample_state,
            pack=minimal_pack,
            receipt=sample_receipt,
            max_bytes=100,
        )
