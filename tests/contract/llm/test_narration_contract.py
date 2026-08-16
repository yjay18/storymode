"""Contract tests for NarrationV1 (LLM-06)."""

import pytest
from pydantic import ValidationError

from llm.contracts.narration import NarrationV1


def test_narration_v1_valid_contract() -> None:
    data = {
        "contract_version": 1,
        "prompt_version": "narrator/1.0.0",
        "request_id": "req-narr-123",
        "narration": "You step into the shadowy chamber as ancient dust swirls around your boots.",
        "speaker_ordinals_used": [1],
        "fact_ordinals_referenced": [],
    }

    narration = NarrationV1.model_validate(data)
    assert narration.contract_version == 1
    assert narration.prompt_version == "narrator/1.0.0"
    assert narration.request_id == "req-narr-123"
    assert "shadowy chamber" in narration.narration
    assert narration.speaker_ordinals_used == [1]


def test_narration_v1_invalid_contract_version() -> None:
    data = {
        "contract_version": 2,  # Invalid version
        "prompt_version": "narrator/1.0.0",
        "request_id": "req-narr-123",
        "narration": "Some narrative text.",
        "speaker_ordinals_used": [],
        "fact_ordinals_referenced": [],
    }
    with pytest.raises(ValidationError):
        NarrationV1.model_validate(data)


def test_narration_v1_empty_narration_rejected() -> None:
    data = {
        "contract_version": 1,
        "prompt_version": "narrator/1.0.0",
        "request_id": "req-narr-123",
        "narration": "",  # Empty string rejected by min_length=1
        "speaker_ordinals_used": [],
        "fact_ordinals_referenced": [],
    }
    with pytest.raises(ValidationError):
        NarrationV1.model_validate(data)
