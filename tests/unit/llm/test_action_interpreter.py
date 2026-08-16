"""Unit tests for action interpretation orchestration and one-shot repair (LLM-05)."""

import json
from typing import Any

import httpx
import pytest

from llm.contracts.action import ActionProposal
from llm.ollama_client import OllamaClient
from llm.orchestration.action_interpreter import (
    ActionInterpreter,
    FailureReason,
    InterpretationFailure,
    InterpretationSuccess,
)
from llm.prompts.action_interpreter_v1 import ACTION_INTERPRETER_PROMPT_VERSION
from llm.retrieval.action_context import (
    ActionContextPacketV1,
    CandidateEntry,
    KnownFactEntry,
)


@pytest.fixture
def sample_packet() -> ActionContextPacketV1:
    return ActionContextPacketV1(
        schema_version=1,
        request_id="req-interp-1",
        location_id="area-1",
        location_name="Ancient Crypt",
        location_danger_level=2,
        location_summary="A cold, damp stone crypt.",
        candidates=[
            CandidateEntry(ordinal=1, id="comp-1", type="companion", name="Kael"),
            CandidateEntry(ordinal=2, id="obj-sarcophagus", type="object", name="Sarcophagus"),
        ],
        known_facts=[
            KnownFactEntry(
                ordinal=1, fact_id="fact-1", summary="The crypt is guarded by skeletons."
            )
        ],
        raw_player_input="Pry open the sarcophagus with a crowbar.",
    )


def _valid_proposal_dict(request_id: str = "req-interp-1", ordinal: int = 2) -> dict[str, Any]:
    return {
        "contract_version": 1,
        "prompt_version": ACTION_INTERPRETER_PROMPT_VERSION,
        "request_id": request_id,
        "status": "valid",
        "operation": "alter_environment",
        "verb": "pry open",
        "entity_mentions": [
            {
                "text": "sarcophagus",
                "role": "target",
                "candidate_ordinal": ordinal,
            }
        ],
        "capability_mentions": [],
        "intended_effect": "Open the sarcophagus.",
        "challenge_label": "standard",
        "uncertainty_reason": "Heavy stone lid.",
        "stakes": ["Open the lid or make loud noise."],
        "reinterpretation": None,
        "redirect": None,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_interpret_action_valid_first_attempt(
    sample_packet: ActionContextPacketV1,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps(_valid_proposal_dict()),
                }
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    interpreter = ActionInterpreter(ollama_client=client)

    result = await interpreter.interpret_action(sample_packet)

    assert isinstance(result, InterpretationSuccess)
    assert result.attempts == 1
    assert result.repaired is False
    assert isinstance(result.proposal, ActionProposal)
    assert result.proposal.verb == "pry open"


@pytest.mark.anyio
async def test_interpret_action_repaired_on_second_attempt(
    sample_packet: ActionContextPacketV1,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            # First attempt: malformed response with invalid candidate ordinal 99
            bad_dict = _valid_proposal_dict(ordinal=99)
            return httpx.Response(
                status_code=200,
                json={"message": {"role": "assistant", "content": json.dumps(bad_dict)}},
            )
        # Second attempt (repair): valid response
        return httpx.Response(
            status_code=200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps(_valid_proposal_dict(ordinal=2)),
                }
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    interpreter = ActionInterpreter(ollama_client=client)

    result = await interpreter.interpret_action(sample_packet)

    assert isinstance(result, InterpretationSuccess)
    assert result.attempts == 2
    assert result.repaired is True
    assert result.proposal.entity_mentions[0].candidate_ordinal == 2


@pytest.mark.anyio
async def test_interpret_action_fails_after_two_malformed_attempts(
    sample_packet: ActionContextPacketV1,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={"message": {"role": "assistant", "content": "not json"}},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    interpreter = ActionInterpreter(ollama_client=client)

    result = await interpreter.interpret_action(sample_packet)

    assert isinstance(result, InterpretationFailure)
    assert result.attempts == 2
    assert result.repaired is False
    assert result.reason == FailureReason.PARSING_ERROR


@pytest.mark.anyio
async def test_interpret_action_request_id_mismatch(
    sample_packet: ActionContextPacketV1,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        bad_id_dict = _valid_proposal_dict(request_id="wrong-id-999")
        return httpx.Response(
            status_code=200,
            json={"message": {"role": "assistant", "content": json.dumps(bad_id_dict)}},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    interpreter = ActionInterpreter(ollama_client=client)

    result = await interpreter.interpret_action(sample_packet)

    assert isinstance(result, InterpretationFailure)
    assert result.attempts == 2
    assert result.reason == FailureReason.REQUEST_ID_MISMATCH


@pytest.mark.anyio
async def test_interpret_action_timeout_fails_fast_without_repair(
    sample_packet: ActionContextPacketV1,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("Timeout")

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    interpreter = ActionInterpreter(ollama_client=client)

    result = await interpreter.interpret_action(sample_packet)

    assert isinstance(result, InterpretationFailure)
    assert result.attempts == 1
    assert result.reason == FailureReason.TIMEOUT
    assert calls == 1  # No retry on timeout
