"""Runtime opportunity proposal validation independent of LLM transport (PLOT-03)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal

from pydantic import Field

from domain.models.common import DisplayString, EntityId, FrozenModel
from domain.models.plot import OpportunityDefinition, PlotFile
from domain.models.plot_state import OpportunityInstance
from domain.models.runtime_state import RuntimeState


class OpportunityProposalV1(FrozenModel):
    """The typed JSON contract for an LLM-generated opportunity proposal."""

    schema_version: Literal[1] = 1
    request_id: EntityId
    parent_milestone_ordinal: int
    title: DisplayString
    description: DisplayString
    entity_ordinals: list[int] = Field(default_factory=list)
    approach_tags: list[DisplayString] = Field(default_factory=list)
    allowed_outcome_ordinals: list[int] = Field(min_length=1)
    precondition_ordinals: list[int] = Field(default_factory=list)
    expiry_condition_ordinals: list[int] = Field(min_length=1)
    challenge_label: DisplayString
    pacing_reason: DisplayString
    canonical_claims: list[DisplayString] = Field(default_factory=list)
    balance_rating: Annotated[int, Field(ge=1, le=100)] = 50


class OpportunityCandidateSet(FrozenModel):
    """The bounded candidate tables provided to the LLM for ordinal references."""

    milestones: list[EntityId]
    entities: list[EntityId]
    outcomes: list[EntityId]
    predicates: list[DisplayString]

    def get_milestone(self, ordinal: int) -> EntityId | None:
        """1-based ordinal lookup for milestones."""
        if 1 <= ordinal <= len(self.milestones):
            return self.milestones[ordinal - 1]
        return None

    def get_entity(self, ordinal: int) -> EntityId | None:
        """1-based ordinal lookup for entities."""
        if 1 <= ordinal <= len(self.entities):
            return self.entities[ordinal - 1]
        return None

    def get_outcome(self, ordinal: int) -> EntityId | None:
        """1-based ordinal lookup for outcomes."""
        if 1 <= ordinal <= len(self.outcomes):
            return self.outcomes[ordinal - 1]
        return None

    def get_predicate(self, ordinal: int) -> DisplayString | None:
        """1-based ordinal lookup for predicates."""
        if 1 <= ordinal <= len(self.predicates):
            return self.predicates[ordinal - 1]
        return None


class ProposalValidationResult(FrozenModel):
    """Result of validating an OpportunityProposalV1."""

    is_valid: bool
    diagnostics: list[str] = Field(default_factory=list)
    opportunity_def: OpportunityDefinition | None = None
    opportunity_instance: OpportunityInstance | None = None


def validate_opportunity_proposal(
    proposal: OpportunityProposalV1,
    candidate_set: OpportunityCandidateSet,
    state: RuntimeState,
    plot_file: PlotFile,
    id_generator: Callable[[], EntityId],
) -> ProposalValidationResult:
    """Validate a runtime opportunity proposal and assign ID only on success.

    Guarantees:
    - Rejects any canonical claims in v1 (protected truth cannot be fabricated).
    - Resolves ordinals strictly against candidate_set.
    - Validates parent milestone is active/reachable in state.
    - Validates referenced entities, outcomes, preconditions, and expiry conditions.
    - Rejects duplicate active titles (novelty check).
    - If invalid, consumes no ID from generator and produces no state mutation.
    """
    diagnostics: list[str] = []

    # 1. Protected truth / canonical claims check: must be empty in v1
    if proposal.canonical_claims:
        diagnostics.append(
            f"Proposal contains {len(proposal.canonical_claims)} canonical claims; "
            "runtime proposals cannot fabricate canonical truth or world laws."
        )

    # 2. Parent milestone resolution & reachability
    parent_m = candidate_set.get_milestone(proposal.parent_milestone_ordinal)
    if parent_m is None:
        diagnostics.append(
            f"Invalid parent_milestone_ordinal {proposal.parent_milestone_ordinal}: "
            f"out of range (1..{len(candidate_set.milestones)})"
        )
    elif parent_m not in state.plot.current_milestone_ids:
        diagnostics.append(
            f"Parent milestone '{parent_m}' is not an active current milestone: "
            f"{state.plot.current_milestone_ids}"
        )

    # 3. Entity ordinals resolution
    referenced_entities: list[EntityId] = []
    for ord_idx in proposal.entity_ordinals:
        ent = candidate_set.get_entity(ord_idx)
        if ent is None:
            diagnostics.append(f"Invalid entity_ordinal {ord_idx}: candidate not found")
        else:
            referenced_entities.append(ent)

    # 4. Allowed outcome ordinals resolution
    allowed_outcomes: list[EntityId] = []
    for ord_idx in proposal.allowed_outcome_ordinals:
        out = candidate_set.get_outcome(ord_idx)
        if out is None:
            diagnostics.append(f"Invalid allowed_outcome_ordinal {ord_idx}: candidate not found")
        else:
            allowed_outcomes.append(out)

    if not allowed_outcomes and not diagnostics:
        diagnostics.append("Proposal must define at least one valid allowed outcome")

    # 5. Precondition ordinals resolution
    preconditions: list[DisplayString] = []
    for ord_idx in proposal.precondition_ordinals:
        pred = candidate_set.get_predicate(ord_idx)
        if pred is None:
            diagnostics.append(f"Invalid precondition_ordinal {ord_idx}: candidate not found")
        else:
            preconditions.append(pred)

    # 6. Expiry condition ordinals resolution
    expiry_conditions: list[DisplayString] = []
    for ord_idx in proposal.expiry_condition_ordinals:
        pred = candidate_set.get_predicate(ord_idx)
        if pred is None:
            diagnostics.append(f"Invalid expiry_condition_ordinal {ord_idx}: candidate not found")
        else:
            expiry_conditions.append(pred)

    if not expiry_conditions and not diagnostics:
        diagnostics.append("Proposal must define at least one valid expiry condition")

    # 7. Novelty check: title must not duplicate an existing authored or runtime opportunity
    for opp_def in plot_file.authored_opportunities:
        if str(opp_def.title).strip().lower() == str(proposal.title).strip().lower():
            diagnostics.append(
                f"Proposal title '{proposal.title}' duplicates existing authored opportunity"
            )
            break

    # 8. If diagnostics exist, reject without generating ID
    if diagnostics:
        return ProposalValidationResult(
            is_valid=False,
            diagnostics=diagnostics,
        )

    # All validations passed -> assign new ID
    new_id = id_generator()
    assert parent_m is not None  # Guarded above

    opp_def = OpportunityDefinition(
        id=new_id,
        parent_milestone_id=parent_m,
        title=proposal.title,
        description=proposal.description,
        referenced_entity_ids=referenced_entities,
        allowed_outcome_ids=allowed_outcomes,
        preconditions=preconditions,
        expiry_conditions=expiry_conditions,
        balance_rating=proposal.balance_rating,
    )

    opp_instance = OpportunityInstance(
        opportunity_id=new_id,
        parent_id=parent_m,
        origin_id=proposal.request_id,
        is_resolved=False,
    )

    return ProposalValidationResult(
        is_valid=True,
        diagnostics=[],
        opportunity_def=opp_def,
        opportunity_instance=opp_instance,
    )
