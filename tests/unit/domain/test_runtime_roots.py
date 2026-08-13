"""Tests for runtime state roots."""

import datetime
import pytest

from domain.models.audit import JournalEvent, RollRecord
from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.narrative_memory import NarrativeMemory
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import ResourceValue
from domain.models.runtime_state import CommandReceipt, RuntimeState
from domain.models.save_meta import SaveMeta
from domain.models.world_state import LocationState


@pytest.fixture
def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


@pytest.fixture
def base_player() -> PlayerState:
    return PlayerState(
        id="hero",
        name="Hero",
        background_id="bg-1",
        stats=StatBlock(strength=10, dexterity=10, intelligence=10, charisma=10, constitution=10, wisdom=10),
        hp=ResourceValue(current=10, maximum=10),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=10, maximum=10),
        mana_regen=2,
        speed=30,
        luck_capacity=3,
    )


def test_runtime_state_invariants(base_player: PlayerState) -> None:
    # Too many receipts
    receipts = [
        CommandReceipt(
            command_id=f"cmd-{i}",
            canonical_request_hash="hash",
            committed_revision=i,
            result_kind="success",
            safe_result_summary="ok"
        )
        for i in range(101)
    ]
    with pytest.raises(ValueError, match="cannot exceed 100"):
        RuntimeState(
            campaign_id="camp-1",
            campaign_version="1.0.0",
            campaign_fingerprint="fp",
            save_id="save-1",
            revision=100,
            last_command_receipts=receipts,
            difficulty=DefaultDifficulty.NORMAL,
            player=base_player,
            party=PartyState(protagonist_id="hero"),
            location=LocationState(area_id="town"),
            plot=PlotState(),
        )

    # Revision trailing receipts
    bad_receipts = [
        CommandReceipt(
            command_id="cmd-1",
            canonical_request_hash="hash",
            committed_revision=5,
            result_kind="success",
            safe_result_summary="ok"
        )
    ]
    with pytest.raises(ValueError, match="cannot trail a committed command receipt"):
        RuntimeState(
            campaign_id="camp-1",
            campaign_version="1.0.0",
            campaign_fingerprint="fp",
            save_id="save-1",
            revision=4, # < 5
            last_command_receipts=bad_receipts,
            difficulty=DefaultDifficulty.NORMAL,
            player=base_player,
            party=PartyState(protagonist_id="hero"),
            location=LocationState(area_id="town"),
            plot=PlotState(),
        )


def test_audit_logs_utc(utc_now: datetime.datetime) -> None:
    naive_dt = datetime.datetime.now()
    
    with pytest.raises(ValueError, match="recorded_at must be UTC"):
        JournalEvent(
            event_id="e-1",
            transaction_id="tx-1",
            revision=1,
            event_index=0,
            recorded_at=naive_dt,
            command_id="cmd-1",
            event_type="info",
        )
        
    with pytest.raises(ValueError, match="recorded_at must be UTC"):
        RollRecord(
            roll_id="r-1",
            transaction_id="tx-1",
            revision=1,
            recorded_at=naive_dt,
            command_id="cmd-1",
            reason="attack",
            die_sides=20,
            raw_rolls=[10],
            selected_roll_index=0,
            total=10,
        )


def test_roll_record_bounds(utc_now: datetime.datetime) -> None:
    # Invalid raw roll
    with pytest.raises(ValueError, match="out of bounds"):
        RollRecord(
            roll_id="r-1",
            transaction_id="tx-1",
            revision=1,
            recorded_at=utc_now,
            command_id="cmd-1",
            reason="attack",
            die_sides=20,
            raw_rolls=[21], # invalid for d20
            selected_roll_index=0,
            total=21,
        )
        
    # Invalid selected index
    with pytest.raises(ValueError, match="selected_roll_index is out of bounds"):
        RollRecord(
            roll_id="r-1",
            transaction_id="tx-1",
            revision=1,
            recorded_at=utc_now,
            command_id="cmd-1",
            reason="attack",
            die_sides=20,
            raw_rolls=[10],
            selected_roll_index=1, # size is 1, max index is 0
            total=10,
        )


def test_narrative_memory_size_limit() -> None:
    mem = NarrativeMemory(
        campaign_id="camp-1",
        campaign_version="1.0.0",
        save_id="save-1",
        derived_from_revision=1,
        recent_events=["Event 1", "Event 2", "Event 3"],
        current_objective="Obj",
    )
    assert mem.campaign_id == "camp-1"
    
    # Create a large dictionary to exceed the 32 KiB limit without exceeding DisplayString 120 char limit
    large_dict = {
        f"entity-{i:04d}": "A" * 100 for i in range(400)
    }
    
    with pytest.raises(ValueError, match="exceeds 32 KiB"):
        NarrativeMemory(
            campaign_id="camp-1",
            campaign_version="1.0.0",
            save_id="save-1",
            derived_from_revision=1,
            recent_events=["Event 1", "Event 2", "Event 3"],
            current_objective="Obj",
            relationship_summaries=large_dict,
        )
