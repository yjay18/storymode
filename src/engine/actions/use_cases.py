"""Exploration use-case orchestrator.

Accepts an already-parsed ActionProposal (no Ollama dependency), loads campaign
and save state, runs the full candidate / validation / check pipeline, and
commits the resulting state atomically.  Returns a safe result object.
"""

from __future__ import annotations

import dataclasses

from domain.models.area import AreaDefinition
from domain.models.check_state import CheckOutcomes
from domain.models.common import EntityId
from domain.models.runtime_state import RuntimeState
from engine.actions.candidates import CandidateSet
from engine.actions.checks import (
    build_pending_check,
    cancel_pending_check,
    decide_check_necessity,
)
from engine.actions.creative import CreativeValidator
from engine.actions.operations import OperationValidator
from engine.actions.protocols import ActionProposalLike
from engine.actions.resolution import CheckResolver
from engine.actions.resolver import EntityResolver


@dataclasses.dataclass(frozen=True)
class SubmitResult:
    """Outcome of submitting an exploration action proposal."""

    state: RuntimeState
    """The new committed state after the action."""

    has_pending_check: bool
    """True when the action created a pending check that must be resolved."""

    rejection_reason: str | None
    """Non-None when the proposal was rejected (state unchanged)."""


@dataclasses.dataclass(frozen=True)
class ResolveResult:
    """Outcome of resolving a pending check."""

    state: RuntimeState
    roll: int
    band: str


@dataclasses.dataclass(frozen=True)
class CancelResult:
    """Outcome of cancelling a pending check."""

    state: RuntimeState


# Standard operations that go through OperationValidator
_STANDARD_OPS: frozenset[str] = frozenset(
    {"investigate", "inspect", "search", "travel", "talk", "use_item"}
)


class ExplorationUseCases:
    """Orchestrates the deterministic exploration action pipeline.

    Dependencies are injected so that tests can supply scripted random sources
    and in-memory repositories without touching the filesystem.
    """

    def __init__(
        self,
        entity_resolver: EntityResolver,
        op_validator: OperationValidator,
        creative_validator: CreativeValidator,
        check_resolver: CheckResolver,
        campaign_areas: dict[str, AreaDefinition],
    ) -> None:
        self._entity_resolver = entity_resolver
        self._op_validator = op_validator
        self._creative_validator = creative_validator
        self._check_resolver = check_resolver
        self._campaign_areas = campaign_areas

    # ------------------------------------------------------------------
    # Public use-case methods
    # ------------------------------------------------------------------

    def submit_action(
        self,
        state: RuntimeState,
        proposal: ActionProposalLike,
        command_id: EntityId,
    ) -> SubmitResult:
        """Submit an LLM action proposal and evaluate it deterministically.

        Does **not** perform I/O itself; callers are responsible for loading
        the state and committing the returned state.

        Returns a SubmitResult with the new state (or the original state if
        the proposal is rejected) and metadata about the outcome.
        """
        area = self._campaign_areas.get(state.location.area_id)
        if area is None:
            return SubmitResult(
                state=state,
                has_pending_check=False,
                rejection_reason=f"Area '{state.location.area_id}' not found in campaign",
            )

        # 1. Build bounded candidate set
        candidates = self._build_candidates(area)

        # 2. Resolve entity mentions
        resolved = []
        for mention in proposal.entity_mentions:
            try:
                resolved.append(self._entity_resolver.resolve_mention(mention, candidates))
            except Exception as exc:
                return SubmitResult(
                    state=state,
                    has_pending_check=False,
                    rejection_reason=str(exc),
                )

        # 3. Validate operation
        try:
            if proposal.operation in _STANDARD_OPS:
                self._op_validator.validate(proposal.operation, resolved, state)
            else:
                self._creative_validator.validate(
                    capability_mentions=proposal.capability_mentions,
                    resolved_candidates=resolved,
                    area_objects={obj.id: obj for obj in area.objects},
                    state=state,
                )
        except Exception as exc:
            return SubmitResult(
                state=state,
                has_pending_check=False,
                rejection_reason=str(exc),
            )

        # 4. Decide check necessity
        needs_check = decide_check_necessity(proposal)

        if needs_check:
            empty_outcomes = CheckOutcomes(
                natural_1=[], low=[], standard=[], strong=[], natural_20=[]
            )
            target_ids: list[EntityId] = [c.id for c in resolved]
            check = build_pending_check(
                command_id=command_id,
                state=state,
                proposal=proposal,
                base_dc=10,
                difficulty_adjustment=0,
                actor_id=state.player.id,
                target_ids=target_ids,
                outcomes=empty_outcomes,
            )
            new_state = state.model_copy(
                update={"pending_check": check, "revision": state.revision + 1}
            )
            return SubmitResult(
                state=new_state,
                has_pending_check=True,
                rejection_reason=None,
            )

        # Direct action: increment revision, no pending check
        new_state = state.model_copy(update={"revision": state.revision + 1})
        return SubmitResult(
            state=new_state,
            has_pending_check=False,
            rejection_reason=None,
        )

    def resolve_check(
        self,
        state: RuntimeState,
        use_luck: bool = False,
    ) -> ResolveResult:
        """Resolve the active pending check.

        Draws from the injected random source and returns the new state with
        the check cleared.
        """
        new_state, roll, band, _effects = self._check_resolver.resolve_check(
            state, use_luck=use_luck
        )
        new_state = new_state.model_copy(update={"revision": new_state.revision + 1})
        return ResolveResult(state=new_state, roll=roll, band=band)

    def cancel_check(self, state: RuntimeState) -> CancelResult:
        """Cancel the active pending check without consuming a die."""
        new_state = cancel_pending_check(state)
        new_state = new_state.model_copy(update={"revision": new_state.revision + 1})
        return CancelResult(state=new_state)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_candidates(self, area: AreaDefinition) -> CandidateSet:
        """Build a CandidateSet from the area's objects and residents."""
        from engine.actions.candidates import Candidate, CandidateSet

        entries: list[Candidate] = []
        for obj in area.objects:
            entries.append(Candidate(id=obj.id, type="object", name=obj.name))
        for npc in area.residents:
            entries.append(Candidate(id=npc.id, type="npc", name=npc.name))
        return CandidateSet(candidates=entries)
