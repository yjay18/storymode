"""Narrator orchestration with one-shot repair and deterministic fallback (LLM-07).

Guarantees:
- Validates contract version, prompt version, request_id, and present speaker ordinals.
- Exactly ONE repair attempt on schema/speaker validation failure.
- Never throws exceptions to callers: always falls back to deterministic narration on failure.
- Never rolls dice or mutates game state.
"""

from __future__ import annotations

import json
import re

from llm.contracts.narration import NarrationV1
from llm.ollama_client import (
    ChatMessage,
    OllamaClient,
    OllamaConnectionError,
    OllamaOversizedResponseError,
    OllamaTimeoutError,
)
from llm.orchestration.fallback import generate_deterministic_fallback_narration
from llm.prompts.narrator_v1 import NARRATOR_PROMPT_VERSION, render_narrator_prompt
from llm.retrieval.narrator_context import NarratorContextPacketV1

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_and_validate_narration(
    raw_text: str, packet: NarratorContextPacketV1
) -> tuple[NarrationV1 | None, str | None]:
    """Parse and validate NarrationV1 output from raw text.

    Returns (narration, error_message).
    """
    matches = _JSON_BLOCK_RE.findall(raw_text)
    if not matches:
        trimmed = raw_text.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            json_str = trimmed
        else:
            return None, "No JSON object found in response"
    elif len(matches) > 1:
        return None, "Multiple ambiguous JSON blocks found in response"
    else:
        json_str = matches[0]

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return None, f"Malformed JSON: {e}"

    if not isinstance(data, dict):
        return None, "Parsed JSON is not an object"

    try:
        narration = NarrationV1.model_validate(data)
    except Exception as e:
        return None, f"NarrationV1 schema validation failed: {e}"

    if narration.contract_version != 1:
        return None, f"Contract version mismatch: expected 1, got {narration.contract_version}"

    if narration.prompt_version != NARRATOR_PROMPT_VERSION:
        return (
            None,
            f"Prompt version mismatch: expected '{NARRATOR_PROMPT_VERSION}', "
            f"got '{narration.prompt_version}'",
        )

    if narration.request_id != packet.request_id:
        return (
            None,
            f"Request ID mismatch: expected '{packet.request_id}', got '{narration.request_id}'",
        )

    # Validate speaker ordinals used
    max_speaker_ordinal = len(packet.present_speakers)
    for sp_ord in narration.speaker_ordinals_used:
        if not (1 <= sp_ord <= max_speaker_ordinal):
            return (
                None,
                f"Speaker ordinal {sp_ord} is invalid (must be 1..{max_speaker_ordinal})",
            )

    return narration, None


class NarratorOrchestrator:
    """Orchestrates generation of descriptive narrative prose with fallback safety."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        model_name: str = "llama3.1:8b",
        timeout: float = 30.0,
    ) -> None:
        self.client = ollama_client
        self.model_name = model_name
        self.timeout = timeout

    async def narrate(self, packet: NarratorContextPacketV1) -> str:
        """Generate narrative prose for a committed event, with one repair attempt and fallback."""
        prompt_messages = render_narrator_prompt(packet)

        # Attempt 1
        try:
            resp = await self.client.chat(
                model=self.model_name,
                messages=prompt_messages,
                format_json=True,
                timeout=self.timeout,
            )
        except (
            OllamaTimeoutError,
            OllamaOversizedResponseError,
            OllamaConnectionError,
            Exception,
        ):
            return generate_deterministic_fallback_narration(packet)

        narration, error_msg = _extract_and_validate_narration(resp.message.content, packet)
        if narration is not None:
            return narration.narration

        # Attempt 2: Exactly one repair request with diagnostic error
        repair_messages = list(prompt_messages)
        repair_messages.append(ChatMessage(role="assistant", content=resp.message.content))
        repair_messages.append(
            ChatMessage(
                role="user",
                content=(
                    f"Your output failed validation with error:\n{error_msg}\n\n"
                    "Please correct the error. Output ONLY valid JSON adhering to NarrationV1 "
                    f"for request_id '{packet.request_id}' and prompt_version "
                    f"'{NARRATOR_PROMPT_VERSION}'."
                ),
            )
        )

        try:
            repair_resp = await self.client.chat(
                model=self.model_name,
                messages=repair_messages,
                format_json=True,
                timeout=self.timeout,
            )
        except Exception:
            return generate_deterministic_fallback_narration(packet)

        repaired_narration, _ = _extract_and_validate_narration(repair_resp.message.content, packet)
        if repaired_narration is not None:
            return repaired_narration.narration

        # If repair also failed, return deterministic fallback
        return generate_deterministic_fallback_narration(packet)
