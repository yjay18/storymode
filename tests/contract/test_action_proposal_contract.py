"""Tests for action proposal contract."""

import pytest
from pydantic import ValidationError

from llm.orchestration.json_parser import parse_llm_response


def test_parse_valid_json_block() -> None:
    text = """Some thought process.
    
```json
{
  "contract_version": 1,
  "prompt_version": "1.0",
  "request_id": "req-1",
  "status": "valid",
  "operation": "inspect",
  "verb": "look",
  "entity_mentions": [{"text": "the room", "role": "target", "candidate_ordinal": 1}],
  "capability_mentions": [],
  "intended_effect": "Look around the room",
  "challenge_label": "none",
  "uncertainty_reason": null,
  "stakes": [],
  "reinterpretation": null,
  "redirect": null
}
```
"""
    proposal = parse_llm_response(text)
    assert proposal.contract_version == 1
    assert proposal.status == "valid"
    assert proposal.operation == "inspect"


def test_parse_missing_block() -> None:
    text = "Just some text, no JSON."
    with pytest.raises(ValueError, match="No JSON block found"):
        parse_llm_response(text)


def test_parse_malformed_json() -> None:
    text = """
```json
{
  "contract_version": 1,
  "prompt_version": "1.0",
  "request_id": "req-1",
  "status": "valid" }
}
```
"""
    with pytest.raises(ValueError, match="Malformed JSON"):
        parse_llm_response(text)


def test_parse_extra_fields() -> None:
    text = """
```json
{
  "contract_version": 1,
  "prompt_version": "1.0",
  "request_id": "req-1",
  "status": "valid",
  "operation": "inspect",
  "verb": "look",
  "entity_mentions": [],
  "capability_mentions": [],
  "intended_effect": "Look",
  "challenge_label": "none",
  "uncertainty_reason": null,
  "stakes": [],
  "reinterpretation": null,
  "redirect": null,
  "die_roll": 20
}
```
"""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        parse_llm_response(text)


def test_parse_missing_fields() -> None:
    text = """
```json
{
  "contract_version": 1,
  "prompt_version": "1.0",
  "request_id": "req-1"
}
```
"""
    with pytest.raises(ValidationError, match="Field required"):
        parse_llm_response(text)
