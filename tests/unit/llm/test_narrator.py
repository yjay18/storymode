"""Unit tests for NarratorOrchestrator and fallback generation (LLM-07)."""

import json
from typing import Any

import httpx
import pytest

from llm.ollama_client import OllamaClient
from llm.orchestration.fallback import generate_deterministic_fallback_narration
from llm.orchestration.narrator import NarratorOrchestrator
from llm.prompts.narrator_v1 import NARRATOR_PROMPT_VERSION
from llm.retrieval.narrator_context import (
    CommittedRollView,
    NarratorContextPacketV1,
    SpeakerEntry,
)


@pytest.fixture
def sample_narrator_packet() -> NarratorContextPacketV1:
    return NarratorContextPacketV1(
        schema_version=1,
        request_id="req-narr-orchestrate-1",
        committed_revision=3,
        result_kind="investigate",
        safe_result_summary="Discovered an ornate silver key in the desk drawer.",
        location_name="Study",
        location_description="A quiet study filled with old tomes.",
        roll_display=CommittedRollView(
            natural_roll=18,
            modifier=2,
            total=20,
            target_dc=15,
            outcome="success",
        ),
        present_speakers=[
            SpeakerEntry(ordinal=1, id="player-1", name="Hero", role="Protagonist"),
            SpeakerEntry(ordinal=2, id="comp-1", name="Kael", role="Companion"),
        ],
        recent_memories=[],
        active_objectives=[],
        forbidden_claims=[],
        style_guidelines=["Tone: immersive"],
    )


def _valid_narration_dict(
    request_id: str = "req-narr-orchestrate-1",
    speaker_ordinals: list[int] | None = None,
) -> dict[str, Any]:
    return {
        "contract_version": 1,
        "prompt_version": NARRATOR_PROMPT_VERSION,
        "request_id": request_id,
        "narration": "You search through the desk drawer and uncover an ornate silver key.",
        "speaker_ordinals_used": speaker_ordinals if speaker_ordinals is not None else [1],
        "fact_ordinals_referenced": [],
    }


# ---------------------------------------------------------------------------
# Fallback Generator Tests
# ---------------------------------------------------------------------------


def test_deterministic_fallback_with_roll(sample_narrator_packet: NarratorContextPacketV1) -> None:
    text = generate_deterministic_fallback_narration(sample_narrator_packet)
    assert "[SUCCESS Check: 20 vs DC 15]" in text
    assert "Discovered an ornate silver key" in text


def test_deterministic_fallback_without_roll(
    sample_narrator_packet: NarratorContextPacketV1,
) -> None:
    no_roll_packet = sample_narrator_packet.model_copy(update={"roll_display": None})
    text = generate_deterministic_fallback_narration(no_roll_packet)
    assert text == "Discovered an ornate silver key in the desk drawer."


# ---------------------------------------------------------------------------
# Narrator Orchestrator Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_narrator_orchestrator_success_first_attempt(
    sample_narrator_packet: NarratorContextPacketV1,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={"message": {"role": "assistant", "content": json.dumps(_valid_narration_dict())}},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    orchestrator = NarratorOrchestrator(ollama_client=client)

    result = await orchestrator.narrate(sample_narrator_packet)
    assert "uncover an ornate silver key" in result


@pytest.mark.anyio
async def test_narrator_orchestrator_repaired_on_second_attempt(
    sample_narrator_packet: NarratorContextPacketV1,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            # First attempt: invalid speaker ordinal 99
            bad = _valid_narration_dict(speaker_ordinals=[99])
            return httpx.Response(
                status_code=200,
                json={"message": {"role": "assistant", "content": json.dumps(bad)}},
            )
        # Second attempt (repair): valid speaker ordinal 2
        good = _valid_narration_dict(speaker_ordinals=[2])
        return httpx.Response(
            status_code=200,
            json={"message": {"role": "assistant", "content": json.dumps(good)}},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    orchestrator = NarratorOrchestrator(ollama_client=client)

    result = await orchestrator.narrate(sample_narrator_packet)
    assert calls == 2
    assert "uncover an ornate silver key" in result


@pytest.mark.anyio
async def test_narrator_orchestrator_falls_back_on_unrecoverable_error(
    sample_narrator_packet: NarratorContextPacketV1,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=500, text="Internal crash")

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    orchestrator = NarratorOrchestrator(ollama_client=client)

    result = await orchestrator.narrate(sample_narrator_packet)
    # Must never raise: returns fallback text with roll summary
    assert "[SUCCESS Check: 20 vs DC 15]" in result
    assert "Discovered an ornate silver key" in result


@pytest.mark.anyio
async def test_narrator_orchestrator_falls_back_on_timeout(
    sample_narrator_packet: NarratorContextPacketV1,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Timeout")

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OllamaClient(base_url="http://127.0.0.1:11434", client=http_client)
    orchestrator = NarratorOrchestrator(ollama_client=client)

    result = await orchestrator.narrate(sample_narrator_packet)
    assert "[SUCCESS Check: 20 vs DC 15]" in result
