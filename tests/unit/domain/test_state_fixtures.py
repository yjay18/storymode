"""Test that state models correctly load generated fixtures."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from domain.models.runtime_state import RuntimeState


def test_valid_state_fixture() -> None:
    fixture_path = Path("tests/fixtures/state/valid_state.json")
    if not fixture_path.exists():
        pytest.skip("Fixture not generated yet")
        
    content = fixture_path.read_text()
    state = RuntimeState.model_validate_json(content)
    assert state.campaign_id == "camp-1"


def test_invalid_state_fixture() -> None:
    fixture_path = Path("tests/fixtures/state/invalid_state.json")
    if not fixture_path.exists():
        pytest.skip("Fixture not generated yet")
        
    content = fixture_path.read_text()
    
    with pytest.raises(ValidationError) as exc:
        RuntimeState.model_validate_json(content)
        
    assert "revision cannot trail" in str(exc.value)
