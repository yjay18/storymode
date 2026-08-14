"""Tests for party and world runtime models."""

import pytest

from domain.models.party_state import CompanionRuntimeState, LifeState, PartyState
from domain.models.runtime_common import ResourceValue
from domain.models.world_state import LocationState, NpcOverride


def make_companion(
    comp_id: str, is_available: bool = True, life_state: LifeState = LifeState.ALIVE
) -> CompanionRuntimeState:
    return CompanionRuntimeState(
        id=comp_id,
        hp=ResourceValue(current=10, maximum=10),
        armour=ResourceValue(current=0, maximum=5),
        mana=ResourceValue(current=10, maximum=10),
        is_available=is_available,
        life_state=life_state,
    )


def test_companion_contradictory_state() -> None:
    # Dead but available
    with pytest.raises(ValueError, match="a dead companion cannot be available"):
        make_companion("comp-1", is_available=True, life_state=LifeState.DEAD)

    # Dead and unavailable is fine
    c = make_companion("comp-1", is_available=False, life_state=LifeState.DEAD)
    assert c.life_state == LifeState.DEAD


def test_party_max_three_active() -> None:
    comp1 = make_companion("comp-1")
    comp2 = make_companion("comp-2")
    comp3 = make_companion("comp-3")
    comp4 = make_companion("comp-4")

    companions = {c.id: c for c in [comp1, comp2, comp3, comp4]}

    with pytest.raises(ValueError, match="more than 3 active companions"):
        PartyState(
            protagonist_id="hero",
            active_companion_ids=["comp-1", "comp-2", "comp-3", "comp-4"],
            companions=companions,
        )


def test_party_protagonist_duplication() -> None:
    # Protagonist in active list
    comp1 = make_companion("hero")

    with pytest.raises(ValueError, match="protagonist cannot be in active_companion_ids"):
        PartyState(
            protagonist_id="hero",
            active_companion_ids=["hero"],
            companions={"hero": comp1},
        )

    # Protagonist in map
    with pytest.raises(ValueError, match="protagonist cannot be in companions dict"):
        PartyState(
            protagonist_id="hero",
            active_companion_ids=[],
            companions={"hero": comp1},
        )


def test_party_active_must_be_in_map() -> None:
    with pytest.raises(ValueError, match="active companion comp-1 not found"):
        PartyState(
            protagonist_id="hero",
            active_companion_ids=["comp-1"],
            companions={},
        )


def test_party_active_must_be_available_and_alive() -> None:
    comp1 = make_companion("comp-1", is_available=False, life_state=LifeState.ALIVE)
    with pytest.raises(ValueError, match="must be available"):
        PartyState(
            protagonist_id="hero",
            active_companion_ids=["comp-1"],
            companions={"comp-1": comp1},
        )

    comp2 = make_companion("comp-2", is_available=False, life_state=LifeState.CAPTURED)
    with pytest.raises(ValueError, match="must be available"):
        PartyState(
            protagonist_id="hero",
            active_companion_ids=["comp-2"],
            companions={"comp-2": comp2},
        )


def test_party_valid() -> None:
    comp1 = make_companion("comp-1")
    party = PartyState(
        protagonist_id="hero",
        active_companion_ids=["comp-1"],
        companions={"comp-1": comp1},
    )
    assert len(party.active_companion_ids) == 1
    assert party.companions["comp-1"].is_available


def test_location_and_overrides_allow_unknown_values() -> None:
    # Unknown extra override value is rejected via strict mode if we enforce it,
    # but Pydantic's FrozenModel (with extra="forbid") handles this.
    loc = LocationState(area_id="town", discovered_area_ids={"town", "forest"})
    assert loc.area_id == "town"

    with pytest.raises(ValueError):
        # extra field
        NpcOverride(location_area_id="town", unknown_field=True)  # type: ignore
