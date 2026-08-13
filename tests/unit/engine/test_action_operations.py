"""Tests for operation validation."""

import pytest

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.party_state import CompanionRuntimeState, LifeState, PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import InventoryEntry, ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.world_state import LocationState, NpcOverride
from engine.actions.candidates import Candidate
from engine.actions.operations import OperationValidationError, OperationValidator


@pytest.fixture
def mock_state() -> RuntimeState:
    player = PlayerState(
        id="player-1",
        name="Hero",
        background_id="bg-1",
        stats=StatBlock(strength=10, dexterity=10, intelligence=10, charisma=10, constitution=10, wisdom=10),
        hp=ResourceValue(current=10, maximum=10),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=5, maximum=5),
        mana_regen=1,
        speed=30,
        luck_capacity=3,
        inventory=[InventoryEntry(item_id="item-owned", quantity=1)],
    )
    party = PartyState(
        protagonist_id="player-1",
        companions={
            "comp-dead": CompanionRuntimeState(
                id="comp-dead",
                hp=ResourceValue(current=0, maximum=10),
                armour=ResourceValue(current=0, maximum=0),
                mana=ResourceValue(current=0, maximum=0),
                life_state=LifeState.DEAD,
                is_available=False
            )
        }
    )
    return RuntimeState(
        campaign_id="camp-1",
        campaign_version="1.0.0",
        campaign_fingerprint="abc",
        save_id="save-1",
        revision=1,
        difficulty=DefaultDifficulty.NORMAL,
        player=player,
        party=party,
        location=LocationState(area_id="area-1"),
        plot=PlotState(),
        npc_overrides={
            "npc-dead": NpcOverride(life_state=LifeState.DEAD)
        }
    )


def test_validate_travel(mock_state: RuntimeState) -> None:
    validator = OperationValidator()
    
    # Valid
    validator.validate("travel", [Candidate("area-2", "area", "Forest")], mock_state)
    
    # Invalid type
    with pytest.raises(OperationValidationError, match="must be an area"):
        validator.validate("travel", [Candidate("obj-1", "object", "Tree")], mock_state)
        
    # Missing candidate
    with pytest.raises(OperationValidationError, match="requires a destination"):
        validator.validate("travel", [], mock_state)


def test_validate_talk(mock_state: RuntimeState) -> None:
    validator = OperationValidator()
    
    # Valid
    validator.validate("talk", [Candidate("npc-alive", "npc", "Bob")], mock_state)
    
    # Invalid type
    with pytest.raises(OperationValidationError, match="Cannot talk to a object"):
        validator.validate("talk", [Candidate("obj-1", "object", "Tree")], mock_state)
        
    # Dead NPC
    with pytest.raises(OperationValidationError, match="is dead"):
        validator.validate("talk", [Candidate("npc-dead", "npc", "Dead Bob")], mock_state)
        
    # Dead companion
    with pytest.raises(OperationValidationError, match="is dead"):
        validator.validate("talk", [Candidate("comp-dead", "companion", "Dead Comp")], mock_state)


def test_validate_use_item(mock_state: RuntimeState) -> None:
    validator = OperationValidator()
    
    # Valid
    validator.validate("use_item", [Candidate("item-owned", "item", "Potion")], mock_state)
    
    # Missing candidate
    with pytest.raises(OperationValidationError, match="requires an item candidate"):
        validator.validate("use_item", [Candidate("obj-1", "object", "Tree")], mock_state)
        
    # Unowned item
    with pytest.raises(OperationValidationError, match="You do not have"):
        validator.validate("use_item", [Candidate("item-unowned", "item", "Sword")], mock_state)


def test_validate_investigate(mock_state: RuntimeState) -> None:
    validator = OperationValidator()
    
    # Valid
    validator.validate("investigate", [Candidate("obj-1", "object", "Tree")], mock_state)
    
    # Invalid target
    with pytest.raises(OperationValidationError, match="Cannot investigate an entire connected area"):
        validator.validate("investigate", [Candidate("area-2", "area", "Forest")], mock_state)
