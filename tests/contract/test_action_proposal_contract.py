"""Tests for action proposal contract."""

import pytest
from pydantic import ValidationError

from llm.orchestration.json_parser import parse_llm_response


def test_parse_valid_json_block() -> None:
    text = """Some thought process.
    
```json
{
  "intention": "Look around",
  "action_type": "inspect",
  "target_id": "room",
  "payload": {}
}
```
"""
    proposal = parse_llm_response(text)
    assert proposal.intention == "Look around"
    assert proposal.action_type == "inspect"
    assert proposal.target_id == "room"
    assert proposal.payload == {}


def test_parse_missing_block() -> None:
    text = "Just some text, no JSON."
    with pytest.raises(ValueError, match="No JSON block found"):
        parse_llm_response(text)


def test_parse_malformed_json() -> None:
    text = """
```json
{
  "intention": "Look",
  "action_type": "inspect",
  "target_id": "room",
  "payload": }
}
```
"""
    with pytest.raises(ValueError, match="Malformed JSON"):
        parse_llm_response(text)


def test_parse_extra_fields() -> None:
    text = """
```json
{
  "intention": "Look",
  "action_type": "inspect",
  "target_id": "room",
  "payload": {},
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
  "intention": "Look",
  "action_type": "inspect"
}
```
"""
    with pytest.raises(ValidationError, match="Field required"):
        parse_llm_response(text)
