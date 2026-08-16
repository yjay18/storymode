"""Opportunity Planner adapter with one-shot repair and deterministic validation (LLM-08).

Guarantees:
- Orchestrates LLM proposal generation and performs exactly one repair attempt on parse failure.
- Hands proposal strictly to deterministic validate_opportunity_proposal from PLOT-03.
- Consumes no EntityId from id_generator unless validation completely succeeds.
- Never mutates state or corrupts the opportunity frontier on failure.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from domain.models.common import EntityId
from domain.models.pack import CampaignPack
from domain.models.runtime_state import RuntimeState
from engine.plot.proposal_validator import (
    OpportunityCandidateSet,
    OpportunityProposalV1,
    ProposalValidationResult,
    validate_opportunity_proposal,
)
from llm.ollama_client import (
    ChatMessage,
    OllamaClient,
    OllamaConnectionError,
    OllamaOversizedResponseError,
    OllamaTimeoutError,
)
from llm.prompts.opportunity_planner_v1 import (
    OPPORTUNITY_PLANNER_PROMPT_VERSION,
    render_opportunity_prompt,
)
from llm.retrieval.opportunity_context import (
    build_opportunity_context_packet,
)

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_and_parse_proposal(raw_text: str) -> tuple[OpportunityProposalV1 | None, str | None]:
    """Extract and validate JSON matching OpportunityProposalV1."""
    matches = _JSON_BLOCK_RE.findall(raw_text)
    if not matches:
        trimmed = raw_text.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            json_str = trimmed
        else:
            return None, "No JSON block found in response"
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
        proposal = OpportunityProposalV1.model_validate(data)
        return proposal, None
    except Exception as e:
        return None, f"OpportunityProposalV1 schema validation failed: {e}"


class OpportunityPlannerAdapter:
    """Adapter connecting LLM generation to deterministic opportunity validation."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        model_name: str = "llama3.1:8b",
        timeout: float = 30.0,
    ) -> None:
        self.client = ollama_client
        self.model_name = model_name
        self.timeout = timeout

    async def propose_opportunity(
        self,
        state: RuntimeState,
        pack: CampaignPack,
        candidate_set: OpportunityCandidateSet,
        id_generator: Callable[[], EntityId],
        request_id: str = "opp-req-1",
    ) -> ProposalValidationResult:
        """Generate and validate a runtime opportunity proposal."""
        packet = build_opportunity_context_packet(
            request_id=request_id,
            state=state,
            pack=pack,
            candidate_set=candidate_set,
        )

        prompt_messages = render_opportunity_prompt(packet)

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
        ) as e:
            return ProposalValidationResult(
                is_valid=False,
                diagnostics=[f"LLM planner transport error: {e}"],
            )

        proposal, error_msg = _extract_and_parse_proposal(resp.message.content)

        # Attempt 2: Exactly one repair on schema error
        if proposal is None:
            repair_messages = list(prompt_messages)
            repair_messages.append(ChatMessage(role="assistant", content=resp.message.content))
            repair_messages.append(
                ChatMessage(
                    role="user",
                    content=(
                        f"Your output failed validation with error:\n{error_msg}\n\n"
                        "Please correct the error. Output ONLY valid JSON adhering to "
                        f"OpportunityProposalV1 for version '{OPPORTUNITY_PLANNER_PROMPT_VERSION}'."
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
                proposal, _repair_error = _extract_and_parse_proposal(repair_resp.message.content)
            except Exception as e:
                return ProposalValidationResult(
                    is_valid=False,
                    diagnostics=[f"LLM repair transport error: {e}"],
                )

        if proposal is None:
            return ProposalValidationResult(
                is_valid=False,
                diagnostics=[f"Opportunity proposal parsing failed after repair: {error_msg}"],
            )

        # Validate proposal against deterministic validator from PLOT-03
        return validate_opportunity_proposal(
            proposal=proposal,
            candidate_set=candidate_set,
            state=state,
            plot_file=pack.plot,
            id_generator=id_generator,
        )
