"""Plot API request and response schemas (PROG-05)."""

from typing import Annotated

from pydantic import Field

from domain.models.common import DisplayString, EntityId, StrictModel


class ResolveOpportunityRequest(StrictModel):
    """Request to resolve an active opportunity."""

    command_id: EntityId
    expected_revision: Annotated[int, Field(ge=0)]
    opportunity_id: EntityId
    outcome_id: EntityId


class MilestoneView(StrictModel):
    """View model for a plot milestone."""

    id: EntityId
    status: str
    is_current: bool


class OpportunityView(StrictModel):
    """View model for an opportunity."""

    id: EntityId
    title: DisplayString
    description: DisplayString
    status: str
    parent_milestone_id: EntityId
    allowed_outcome_ids: list[EntityId]
    is_resolved: bool


class ClockView(StrictModel):
    """View model for a plot/threat clock."""

    id: EntityId
    current: int
    maximum: int
    completed: bool


class PlotReceiptView(StrictModel):
    """Receipt for plot command."""

    command_id: EntityId
    committed_revision: int
    result_kind: DisplayString
    safe_result_summary: DisplayString


class PlotViewResponse(StrictModel):
    """Overview of plot progression, milestones, opportunities, and clocks."""

    save_id: EntityId
    revision: int
    current_milestone_ids: list[EntityId]
    milestones: list[MilestoneView]
    opportunities: list[OpportunityView]
    clocks: list[ClockView]
    ending_state: DisplayString | None = None


class PlotMutationResponse(StrictModel):
    """Response returned after a plot mutation."""

    save_id: EntityId
    revision: int
    receipt: PlotReceiptView
    plot: PlotViewResponse
