"""Opportunity planner prompt templates and renderer (LLM-08)."""

from __future__ import annotations

from llm.ollama_client import ChatMessage
from llm.retrieval.opportunity_context import OpportunityContextPacketV1

OPPORTUNITY_PLANNER_PROMPT_VERSION = "opportunity-planner/1.0.0"

_PLANNER_SYSTEM_PROMPT = (
    "You are the authoritative Opportunity Planner for the Storymode text RPG.\n"
    "Your role is to propose new runtime narrative opportunities (side objectives, "
    "tactical leads, social hooks) grounded strictly in current active milestones.\n\n"
    "### CONTRACT & RULES\n"
    "1. Ordinal Grounding:\n"
    "   - parent_milestone_ordinal MUST point to an active milestone from the context table.\n"
    "   - entity_ordinals, allowed_outcome_ordinals, precondition_ordinals, and "
    "expiry_condition_ordinals MUST strictly use valid 1-based indices from the provided context.\n"
    "2. Canonical Truth Prohibition:\n"
    "   - 'canonical_claims' MUST BE EMPTY ([]). You cannot invent new world laws or facts.\n"
    "3. Novelty:\n"
    "   - The 'title' must be unique and distinct from active_opportunity_titles.\n"
    "4. Output Contract:\n"
    "   - Output ONLY valid JSON adhering to OpportunityProposalV1.\n"
)

_PLANNER_USER_PROMPT = (
    "<OPPORTUNITY_CONTEXT>\n"
    "{context_json}\n"
    "</OPPORTUNITY_CONTEXT>\n\n"
    "Propose a new runtime opportunity adhering to the rules. "
    "Output ONLY valid OpportunityProposalV1 JSON."
)


def render_opportunity_prompt(packet: OpportunityContextPacketV1) -> list[ChatMessage]:
    """Render the multi-message prompt for the Opportunity Planner."""
    context_json = packet.model_dump_json(indent=2)
    user_content = _PLANNER_USER_PROMPT.format(context_json=context_json)

    return [
        ChatMessage(role="system", content=_PLANNER_SYSTEM_PROMPT),
        ChatMessage(role="user", content=user_content),
    ]
