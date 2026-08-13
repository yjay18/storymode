"""Tests for area, resident, object, encounter, and secret models."""

from typing import Any

import pytest
from pydantic import ValidationError

from domain.models.area import (
    AreaDefinition,
    AreaSecret,
    AreasFile,
)


def make_valid_area(aid: str = "area-1") -> dict[str, Any]:
    return {
        "id": aid,
        "name": "Test Area",
        "major_location_id": "loc-1",
        "description": "A dark place",
        "art_prompt": "Dark place, highly detailed",
        "danger_level": 5,
        "connected_area_ids": [],
        "local_faction_ids": [],
        "residents": [],
        "objects": [],
        "encounters": [],
        "secrets": [],
    }


def make_valid_secret(sid: str = "secret-1", core: bool = False) -> dict[str, Any]:
    d = {
        "id": sid,
        "summary": "A hidden door",
        "lead_fact_ids": [],
        "reveal_conditions": [],
        "core_clue": core,
    }
    if core:
        d["lead_fact_ids"] = ["fact-1"]
        d["reveal_conditions"] = ["perception > 10"]
    return d


def test_core_clue_validation() -> None:
    # Valid non-core
    AreaSecret(**make_valid_secret(core=False))

    # Valid core
    AreaSecret(**make_valid_secret(core=True))

    # Invalid core missing leads
    data = make_valid_secret(core=True)
    data["lead_fact_ids"] = []
    with pytest.raises(ValidationError) as exc:
        AreaSecret(**data)
    assert "core clue must have at least one lead_fact_id" in str(exc.value)

    # Invalid core missing conditions
    data = make_valid_secret(core=True)
    data["reveal_conditions"] = []
    with pytest.raises(ValidationError) as exc:
        AreaSecret(**data)
    assert "core clue must have at least one reveal_condition" in str(exc.value)


def test_area_connections() -> None:
    data = make_valid_area("area-1")

    # Self-connection
    data["connected_area_ids"] = ["area-1"]
    with pytest.raises(ValidationError) as exc:
        AreaDefinition(**data)
    assert "area cannot connect to itself" in str(exc.value)

    # Duplicate connection
    data["connected_area_ids"] = ["area-2", "area-2"]
    with pytest.raises(ValidationError) as exc:
        AreaDefinition(**data)
    assert "duplicate area connections found" in str(exc.value)


def test_area_duplicate_local_ids() -> None:
    data = make_valid_area("area-1")
    data["secrets"] = [
        make_valid_secret("secret-1"),
        make_valid_secret("secret-1"),
    ]
    with pytest.raises(ValidationError) as exc:
        AreaDefinition(**data)
    assert "duplicate local entity IDs found within area" in str(exc.value)


def test_areas_file_smallest_valid() -> None:
    # Smallest one-area root
    AreasFile(
        **{  # type: ignore
            "campaign_id": "test",
            "campaign_version": "1.0.0",
            "areas": [make_valid_area()],
        }
    )


def test_areas_file_duplicate_global_ids() -> None:
    data = {
        "campaign_id": "test",
        "campaign_version": "1.0.0",
        "areas": [
            make_valid_area("area-1"),
            make_valid_area("area-1"),
        ],
    }
    with pytest.raises(ValidationError) as exc:
        AreasFile(**data)  # type: ignore
    assert "duplicate entity IDs found across areas" in str(exc.value)

    area_1 = make_valid_area("area-1")
    area_1["secrets"] = [make_valid_secret("secret-1")]

    area_2 = make_valid_area("area-2")
    area_2["secrets"] = [make_valid_secret("secret-1")]

    data["areas"] = [area_1, area_2]
    with pytest.raises(ValidationError) as exc:
        AreasFile(**data)  # type: ignore
    assert "duplicate entity IDs found across areas" in str(exc.value)
