"""Contract tests for OpportunityProposalV1 (LLM-08)."""

import pytest
from pydantic import ValidationError

from llm.contracts.opportunity import OpportunityProposalV1


def test_opportunity_proposal_v1_valid() -> None:
    data = {
        "schema_version": 1,
        "request_id": "req-opp-1",
        "parent_milestone_ordinal": 1,
        "title": "Investigate Crypt Disturbance",
        "description": "Strange chanting echoes from the crypt.",
        "entity_ordinals": [1, 2],
        "approach_tags": ["stealth", "arcana"],
        "allowed_outcome_ordinals": [1],
        "precondition_ordinals": [],
        "expiry_condition_ordinals": [1],
        "challenge_label": "standard",
        "pacing_reason": "Escalate tension in act 1.",
        "canonical_claims": [],
        "balance_rating": 50,
    }

    prop = OpportunityProposalV1.model_validate(data)
    assert prop.schema_version == 1
    assert prop.parent_milestone_ordinal == 1
    assert prop.title == "Investigate Crypt Disturbance"
    assert prop.canonical_claims == []


def test_opportunity_proposal_v1_invalid_rating() -> None:
    data = {
        "schema_version": 1,
        "request_id": "req-opp-1",
        "parent_milestone_ordinal": 1,
        "title": "Title",
        "description": "Desc",
        "allowed_outcome_ordinals": [1],
        "expiry_condition_ordinals": [1],
        "challenge_label": "easy",
        "pacing_reason": "Pacing",
        "balance_rating": 999,  # Out of range 1..100
    }
    with pytest.raises(ValidationError):
        OpportunityProposalV1.model_validate(data)
