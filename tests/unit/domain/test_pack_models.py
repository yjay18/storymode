"""Tests for campaign pack aggregation."""

import pytest
from pydantic import ValidationError

from domain.models.pack import CampaignPack


def test_pack_validation_failure() -> None:
    # Minimal invalid data to trigger validation failure in nested models
    bad_data = {
        "meta": {"schema_version": 2},  # Invalid schema version
        "style": {},
        "world": {},
        "areas": {},
        "characters": {},
        "skills": {},
        "items": {},
        "enemies": {},
        "plot": {},
        "balance": {},
    }

    with pytest.raises(ValidationError) as exc:
        CampaignPack(**bad_data)  # type: ignore

    assert "meta" in str(exc.value)
    assert "schema_version" in str(exc.value)
