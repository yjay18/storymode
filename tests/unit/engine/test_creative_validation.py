"""Tests for creative capability validation."""

import pytest

from domain.models.area import AreaObject
from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatBlock
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import InventoryEntry, ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.world_state import LocationState
from engine.actions.candidates import Candidate
from engine.actions.creative import CreativeValidator
from engine.actions.operations import OperationValidationError


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
        inventory=[InventoryEntry(item_id="crowbar", quantity=1)],
        non_combat_skill_ranks={"athletics": 2}
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


def test_creative_validate_success(mock_state: RuntimeState) -> None:
    validator = CreativeValidator()
    objects = {
        "crate-1": AreaObject(
            id="crate-1",
            name="Wooden Crate",
            description="A crate",
            location_anchor="Center",
            state="locked",
            interactable_tags=[],
            capability_requirements=["crowbar"],
            allowed_effect_ids=[]
        )
    }
    
    validator.validate(
        capability_mentions=["crowbar"],
        resolved_candidates=[Candidate("crate-1", "object", "Wooden Crate")],
        area_objects=objects,
        state=mock_state
    )


def test_creative_validate_missing_capability(mock_state: RuntimeState) -> None:
    validator = CreativeValidator()
    objects = {
        "crate-1": AreaObject(
            id="crate-1",
            name="Wooden Crate",
            description="A crate",
            location_anchor="Center",
            state="locked",
            interactable_tags=[],
            capability_requirements=["laser"],
            allowed_effect_ids=[]
        )
    }
    
    with pytest.raises(OperationValidationError, match="requires one of: laser"):
        validator.validate(
            capability_mentions=["crowbar"],
            resolved_candidates=[Candidate("crate-1", "object", "Wooden Crate")],
            area_objects=objects,
            state=mock_state
        )


def test_creative_validate_no_requirements(mock_state: RuntimeState) -> None:
    validator = CreativeValidator()
    objects = {
        "crate-1": AreaObject(
            id="crate-1",
            name="Wooden Crate",
            description="A crate",
            location_anchor="Center",
            state="locked",
            interactable_tags=[],
            capability_requirements=[],
            allowed_effect_ids=[]
        )
    }
    
    # Should not raise
    validator.validate(
        capability_mentions=[],
        resolved_candidates=[Candidate("crate-1", "object", "Wooden Crate")],
        area_objects=objects,
        state=mock_state
    )
