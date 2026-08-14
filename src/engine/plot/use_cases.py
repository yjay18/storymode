"""Plot command use cases (PROG-05)."""

from __future__ import annotations

from domain.models.common import DisplayString, EntityId
from domain.models.pack import CampaignPack
from domain.models.runtime_state import CommandReceipt, RuntimeState
from engine.plot.clocks import advance_clock
from engine.plot.milestones import activate_milestone, resolve_milestone
from engine.plot.opportunities import resolve_opportunity
from engine.state.transition import apply_command


class PlotUseCases:
    """Use cases for managing plot progression, milestone transitions, opportunities, and clocks."""

    def __init__(self, pack: CampaignPack) -> None:
        self.pack = pack
        self.clocks_by_id = {c.id: c for c in pack.plot.clock_definitions}

    def resolve_opportunity(
        self,
        state: RuntimeState,
        expected_revision: int,
        command_id: EntityId,
        request_hash: str,
        opportunity_id: EntityId,
        outcome_id: EntityId,
    ) -> tuple[RuntimeState, CommandReceipt]:
        """Resolve an opportunity with an authorized outcome."""

        def mutation(current_state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
            updated_state, _res = resolve_opportunity(
                current_state, opportunity_id, outcome_id, self.pack.plot
            )
            receipt = CommandReceipt(
                command_id=command_id,
                canonical_request_hash=request_hash,
                committed_revision=0,
                result_kind=DisplayString("resolve_opportunity"),
                safe_result_summary=DisplayString(
                    f"Resolved opportunity {opportunity_id} with outcome {outcome_id}"
                ),
            )
            return updated_state, receipt

        return apply_command(
            state=state,
            expected_revision=expected_revision,
            command_id=command_id,
            canonical_request_hash=request_hash,
            mutation_fn=mutation,
        )

    def activate_milestone(
        self,
        state: RuntimeState,
        expected_revision: int,
        command_id: EntityId,
        request_hash: str,
        milestone_id: EntityId,
    ) -> tuple[RuntimeState, CommandReceipt]:
        """Activate an available milestone."""

        def mutation(current_state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
            updated_state = activate_milestone(current_state, milestone_id, self.pack.plot)
            receipt = CommandReceipt(
                command_id=command_id,
                canonical_request_hash=request_hash,
                committed_revision=0,
                result_kind=DisplayString("activate_milestone"),
                safe_result_summary=DisplayString(f"Activated milestone {milestone_id}"),
            )
            return updated_state, receipt

        return apply_command(
            state=state,
            expected_revision=expected_revision,
            command_id=command_id,
            canonical_request_hash=request_hash,
            mutation_fn=mutation,
        )

    def resolve_milestone(
        self,
        state: RuntimeState,
        expected_revision: int,
        command_id: EntityId,
        request_hash: str,
        milestone_id: EntityId,
        outcome_id: EntityId,
    ) -> tuple[RuntimeState, CommandReceipt]:
        """Resolve an active milestone and advance the campaign spine."""

        def mutation(current_state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
            updated_state, _res = resolve_milestone(
                current_state, milestone_id, outcome_id, self.pack.plot
            )
            receipt = CommandReceipt(
                command_id=command_id,
                canonical_request_hash=request_hash,
                committed_revision=0,
                result_kind=DisplayString("resolve_milestone"),
                safe_result_summary=DisplayString(
                    f"Resolved milestone {milestone_id} with outcome {outcome_id}"
                ),
            )
            return updated_state, receipt

        return apply_command(
            state=state,
            expected_revision=expected_revision,
            command_id=command_id,
            canonical_request_hash=request_hash,
            mutation_fn=mutation,
        )

    def advance_clock(
        self,
        state: RuntimeState,
        expected_revision: int,
        command_id: EntityId,
        request_hash: str,
        clock_id: EntityId,
        amount: int = 1,
    ) -> tuple[RuntimeState, CommandReceipt]:
        """Advance a plot or threat clock."""
        if clock_id not in self.clocks_by_id:
            raise ValueError(f"Clock {clock_id} not found in campaign plot definition")

        clock_def = self.clocks_by_id[clock_id]

        def mutation(current_state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
            updated_state, res = advance_clock(current_state, clock_id, clock_def, amount=amount)
            receipt = CommandReceipt(
                command_id=command_id,
                canonical_request_hash=request_hash,
                committed_revision=0,
                result_kind=DisplayString("advance_clock"),
                safe_result_summary=DisplayString(
                    f"Advanced clock {clock_id} to {res.new_value}/{res.maximum}"
                ),
            )
            return updated_state, receipt

        return apply_command(
            state=state,
            expected_revision=expected_revision,
            command_id=command_id,
            canonical_request_hash=request_hash,
            mutation_fn=mutation,
        )
