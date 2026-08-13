"""Tests for world and faction models."""

from typing import Any

import pytest
from pydantic import ValidationError

from domain.models.world import (
    FactionDefinition,
    PowerSystem,
    WorldDefinition,
    WorldFile,
)


def make_valid_power_system() -> dict[str, Any]:
    return {
        "rules": ["Rule 1"],
        "costs": ["Cost 1"],
        "access_restrictions": ["Restriction 1"],
        "side_effects": ["Effect 1"],
    }


def make_valid_faction(fid: str, targets: list[str]) -> dict[str, Any]:
    edges = [{"target_faction_id": t, "stance": 50, "summary": "Neutral"} for t in targets]
    return {
        "id": fid,
        "name": f"Faction {fid}",
        "goals": ["Goal"],
        "resources": ["Resources"],
        "hypocrisy": "Hypocrisy",
        "language_style": "Formal",
        "visual_markings": "Tattoos",
        "relationship_edges": edges,
    }


def make_valid_location(lid: str) -> dict[str, Any]:
    return {
        "id": lid,
        "name": f"Location {lid}",
        "summary": "A big city",
    }


def make_valid_world() -> dict[str, Any]:
    return {
        "name": "Earth",
        "core_conflict": "Conflict",
        "power_system": make_valid_power_system(),
        "values": ["Honour"],
        "factions": [
            make_valid_faction("fac-1", ["fac-2"]),
            make_valid_faction("fac-2", ["fac-1"]),
        ],
        "major_locations": [make_valid_location("loc-1")],
        "material_conditions": ["Poor"],
    }


def test_power_system_non_empty_lists() -> None:
    data = make_valid_power_system()
    data["rules"] = []
    with pytest.raises(ValidationError):
        PowerSystem(**data)


def test_faction_stance_bounds() -> None:
    data = make_valid_faction("fac-1", ["fac-2"])

    # Too low
    data["relationship_edges"][0]["stance"] = -101
    with pytest.raises(ValidationError):
        FactionDefinition(**data)

    # Too high
    data["relationship_edges"][0]["stance"] = 101
    with pytest.raises(ValidationError):
        FactionDefinition(**data)

    # Valid
    data["relationship_edges"][0]["stance"] = -100
    FactionDefinition(**data)
    data["relationship_edges"][0]["stance"] = 100
    FactionDefinition(**data)


def test_faction_self_edge() -> None:
    data = make_valid_faction("fac-1", ["fac-1"])
    with pytest.raises(ValidationError) as exc:
        FactionDefinition(**data)
    assert "cannot have a relationship with itself" in str(exc.value)


def test_faction_duplicate_edges() -> None:
    data = make_valid_faction("fac-1", ["fac-2", "fac-2"])
    with pytest.raises(ValidationError) as exc:
        FactionDefinition(**data)
    assert "duplicate relationship target" in str(exc.value)


def test_world_duplicate_faction_ids() -> None:
    data = make_valid_world()
    data["factions"].append(make_valid_faction("fac-1", []))
    with pytest.raises(ValidationError) as exc:
        WorldDefinition(**data)
    assert "duplicate faction IDs found" in str(exc.value)


def test_world_duplicate_location_ids() -> None:
    data = make_valid_world()
    data["major_locations"].append(make_valid_location("loc-1"))
    with pytest.raises(ValidationError) as exc:
        WorldDefinition(**data)
    assert "duplicate major location IDs found" in str(exc.value)


def test_world_file_valid() -> None:
    WorldFile(**{  # type: ignore
        "campaign_id": "test-campaign",
        "campaign_version": "1.0.0",
        "world": make_valid_world(),
    })


def test_world_file_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        WorldFile(**{  # type: ignore
            "campaign_id": "test-campaign",
            "campaign_version": "1.0.0",
            "world": make_valid_world(),
            "extra": "bad",
        })
