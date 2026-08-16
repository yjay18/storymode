"""Action interpretation orchestration with one-shot repair and typed errors (LLM-05).

Guarantees:
- Validates contract version, prompt version, request_id, and candidate ordinals.
- Exactly ONE repair attempt on schema/ordinal/validation failure with identical facts.
- No repair attempt for timeout or transport unavailability.
- Returns typed InterpretationSuccess or InterpretationFailure without mutating state.
"""

from __future__ import annotations

import enum

from domain.models.common import FrozenModel
from llm.contracts.action import ActionProposal
from llm.ollama_client import (
    ChatMessage,
    OllamaClient,
    OllamaConnectionError,
    OllamaOversizedResponseError,
    OllamaTimeoutError,
)
from llm.orchestration.json_parser import parse_llm_response
from llm.prompts.action_interpreter_v1 import (
    ACTION_INTERPRETER_PROMPT_VERSION,
    render_action_interpreter_prompt,
)
from llm.retrieval.action_context import ActionContextPacketV1


class FailureReason(enum.StrEnum):
    """Categorized failure reasons for action interpretation."""

    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    INVALID_ORDINAL = "invalid_ordinal"
    VERSION_MISMATCH = "version_mismatch"
    REQUEST_ID_MISMATCH = "request_id_mismatch"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    OVERSIZED_RESPONSE = "oversized_response"
    PARSING_ERROR = "parsing_error"


class InterpretationFailure(FrozenModel):
    """Typed result representing a failed action interpretation."""

    request_id: str
    reason: FailureReason
    error_message: str
    attempts: int
    repaired: bool = False


class InterpretationSuccess(FrozenModel):
    """Typed result representing a successfully parsed and validated ActionProposal."""

    proposal: ActionProposal
    attempts: int
    repaired: bool = False


InterpretationResult = InterpretationSuccess | InterpretationFailure


def _validate_and_parse_proposal(
    raw_text: str, packet: ActionContextPacketV1
) -> tuple[ActionProposal | None, FailureReason | None, str | None]:
    """Parse raw LLM response text into ActionProposal and validate against context packet.

    Returns (proposal, failure_reason, error_message).
    """
    try:
        proposal = parse_llm_response(raw_text)
    except ValueError as e:
        return None, FailureReason.PARSING_ERROR, f"Failed to parse ActionProposal JSON: {e}"
    except Exception as e:
        return (
            None,
            FailureReason.SCHEMA_VALIDATION_FAILED,
            f"Schema validation error: {e}",
        )

    # Validate versioning
    if proposal.contract_version != 1:
        return (
            None,
            FailureReason.VERSION_MISMATCH,
            f"Contract version mismatch: expected 1, got {proposal.contract_version}",
        )

    if proposal.prompt_version != ACTION_INTERPRETER_PROMPT_VERSION:
        return (
            None,
            FailureReason.VERSION_MISMATCH,
            f"Prompt version mismatch: expected '{ACTION_INTERPRETER_PROMPT_VERSION}', "
            f"got '{proposal.prompt_version}'",
        )

    # Validate request_id correlation
    if proposal.request_id != packet.request_id:
        return (
            None,
            FailureReason.REQUEST_ID_MISMATCH,
            f"Request ID mismatch: expected '{packet.request_id}', got '{proposal.request_id}'",
        )

    # Validate candidate ordinals
    max_ordinal = len(packet.candidates)
    for mention in proposal.entity_mentions:
        if mention.candidate_ordinal is not None and not (
            1 <= mention.candidate_ordinal <= max_ordinal
        ):
            return (
                None,
                FailureReason.INVALID_ORDINAL,
                (
                    f"Candidate ordinal {mention.candidate_ordinal} is out of bounds "
                    f"(1..{max_ordinal})"
                ),
            )

    return proposal, None, None


class ActionInterpreter:
    """Orchestrates action interpretation with Ollama transport and bounded one-shot repair."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        model_name: str = "llama3.1:8b",
        timeout: float = 30.0,
    ) -> None:
        self.client = ollama_client
        self.model_name = model_name
        self.timeout = timeout

    async def interpret_action(self, packet: ActionContextPacketV1) -> InterpretationResult:
        """Interpret player action, performing at most one repair request on validation failure."""
        prompt_messages = render_action_interpreter_prompt(packet)

        # Attempt 1
        try:
            resp = await self.client.chat(
                model=self.model_name,
                messages=prompt_messages,
                format_json=True,
                timeout=self.timeout,
            )
        except OllamaTimeoutError as e:
            return InterpretationFailure(
                request_id=packet.request_id,
                reason=FailureReason.TIMEOUT,
                error_message=f"LLM request timed out: {e}",
                attempts=1,
                repaired=False,
            )
        except OllamaOversizedResponseError as e:
            return InterpretationFailure(
                request_id=packet.request_id,
                reason=FailureReason.OVERSIZED_RESPONSE,
                error_message=f"LLM response exceeded byte cap: {e}",
                attempts=1,
                repaired=False,
            )
        except (OllamaConnectionError, Exception) as e:
            return InterpretationFailure(
                request_id=packet.request_id,
                reason=FailureReason.UNAVAILABLE,
                error_message=f"LLM service unavailable: {e}",
                attempts=1,
                repaired=False,
            )

        proposal, failure_reason, error_message = _validate_and_parse_proposal(
            resp.message.content, packet
        )

        if proposal is not None:
            return InterpretationSuccess(proposal=proposal, attempts=1, repaired=False)

        # Attempt 2: Exactly one repair request with diagnostic feedback
        assert failure_reason is not None
        assert error_message is not None

        repair_messages = list(prompt_messages)
        repair_messages.append(ChatMessage(role="assistant", content=resp.message.content))
        repair_messages.append(
            ChatMessage(
                role="user",
                content=(
                    f"Your output failed validation with error:\n{error_message}\n\n"
                    "Please correct the error. Output ONLY valid JSON matching ActionProposal "
                    f"for request_id '{packet.request_id}' and prompt_version "
                    f"'{ACTION_INTERPRETER_PROMPT_VERSION}'."
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
        except (OllamaTimeoutError, OllamaConnectionError, Exception) as e:
            return InterpretationFailure(
                request_id=packet.request_id,
                reason=failure_reason,
                error_message=f"Repair failed: {e}",
                attempts=2,
                repaired=False,
            )

        repair_proposal, repair_reason, repair_error = _validate_and_parse_proposal(
            repair_resp.message.content, packet
        )

        if repair_proposal is not None:
            return InterpretationSuccess(proposal=repair_proposal, attempts=2, repaired=True)

        return InterpretationFailure(
            request_id=packet.request_id,
            reason=repair_reason or failure_reason,
            error_message=repair_error or error_message,
            attempts=2,
            repaired=False,
        )
