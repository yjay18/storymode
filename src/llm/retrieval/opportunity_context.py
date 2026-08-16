"""Bounded opportunity planner context packet builder (LLM-08).

Guarantees:
- Provides 1-based candidate tables for milestones, entities, outcomes, and predicates.
- Enforces strict 20 KiB byte budget.
- Excludes hidden / unrevealed secrets and mutable state structures.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from domain.models.common import FrozenModel
from domain.models.pack import CampaignPack
from domain.models.runtime_state import RuntimeState
from engine.plot.proposal_validator import OpportunityCandidateSet

OPPORTUNITY_CONTEXT_MAX_BYTES: int = 20 * 1024  # 20 KiB


class OpportunityContextOverflowError(Exception):
    """Raised when opportunity context data exceeds maximum byte budget."""


class OpportunityContextPacketV1(FrozenModel):
    """Immutable context packet supplied to the Opportunity Planner prompt."""

    schema_version: Literal[1] = 1
    request_id: str
    current_area_id: str
    current_area_name: str
    active_milestones: list[dict[str, Any]] = Field(default_factory=list)
    candidate_entities: list[dict[str, Any]] = Field(default_factory=list)
    allowed_outcomes: list[dict[str, Any]] = Field(default_factory=list)
    available_predicates: list[dict[str, Any]] = Field(default_factory=list)
    active_opportunity_titles: list[str] = Field(default_factory=list)


def build_opportunity_context_packet(
    request_id: str,
    state: RuntimeState,
    pack: CampaignPack,
    candidate_set: OpportunityCandidateSet,
    max_bytes: int = OPPORTUNITY_CONTEXT_MAX_BYTES,
) -> OpportunityContextPacketV1:
    """Build an immutable, bounded OpportunityContextPacketV1."""
    curr_area_id = state.location.area_id
    area_map = {a.id: a for a in pack.areas.areas}
    area = area_map.get(curr_area_id)
    loc_name = str(area.name) if area else curr_area_id

    # 1. Active Milestones table with 1-based ordinals
    milestone_map = {m.id: m for m in pack.plot.milestones}
    ms_table: list[dict[str, Any]] = []
    for i, ms_id in enumerate(candidate_set.milestones, start=1):
        m_def = milestone_map.get(ms_id)
        ms_table.append(
            {
                "ordinal": i,
                "id": str(ms_id),
                "canonical_truth": str(m_def.canonical_truth) if m_def else f"Milestone {ms_id}",
            }
        )

    # 2. Entities table with 1-based ordinals
    entity_table: list[dict[str, Any]] = [
        {"ordinal": i, "id": str(e_id)} for i, e_id in enumerate(candidate_set.entities, start=1)
    ]

    # 3. Outcomes table with 1-based ordinals
    outcome_table: list[dict[str, Any]] = [
        {"ordinal": i, "id": str(o_id)} for i, o_id in enumerate(candidate_set.outcomes, start=1)
    ]

    # 4. Predicates table with 1-based ordinals
    predicate_table: list[dict[str, Any]] = [
        {"ordinal": i, "predicate": str(p)} for i, p in enumerate(candidate_set.predicates, start=1)
    ]

    # 5. Existing active opportunity titles for novelty check
    active_titles: list[str] = []
    opp_map = {o.id: o for o in pack.plot.authored_opportunities}
    for opp_id in state.plot.opportunities:
        o_def = opp_map.get(opp_id)
        if o_def:
            active_titles.append(str(o_def.title))

    packet = OpportunityContextPacketV1(
        schema_version=1,
        request_id=request_id,
        current_area_id=curr_area_id,
        current_area_name=loc_name,
        active_milestones=ms_table,
        candidate_entities=entity_table,
        allowed_outcomes=outcome_table,
        available_predicates=predicate_table,
        active_opportunity_titles=active_titles,
    )

    dumped = packet.model_dump_json().encode("utf-8")
    if len(dumped) > max_bytes:
        raise OpportunityContextOverflowError(
            f"Opportunity context exceeds budget of {max_bytes} bytes ({len(dumped)} bytes)"
        )

    return packet
