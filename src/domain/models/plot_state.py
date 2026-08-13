"""Plot and clock runtime models."""

import enum

from pydantic import Field

from domain.models.common import DisplayString, EntityId, FrozenModel


class MilestoneState(enum.StrEnum):
    """The current state of a milestone."""

    LOCKED = "locked"
    AVAILABLE = "available"
    ACTIVE = "active"
    RESOLVED = "resolved"
    FAILED = "failed"


class OpportunityInstance(FrozenModel):
    """An active or resolved instance of an opportunity."""

    opportunity_id: EntityId
    origin_id: EntityId | None = None
    parent_id: EntityId | None = None
    predecessor_id: EntityId | None = None
    is_resolved: bool = False


class PlotState(FrozenModel):
    """The state of the overarching campaign plot."""

    milestones: dict[EntityId, MilestoneState] = Field(default_factory=dict)
    opportunities: dict[EntityId, OpportunityInstance] = Field(default_factory=dict)
    current_milestone_ids: set[EntityId] = Field(default_factory=set)
    ending_state: DisplayString | None = None


class ClockState(FrozenModel):
    """The runtime state of a progress clock."""

    clock_id: EntityId
    current: int = Field(ge=0)
    maximum: int = Field(ge=1)
    completed: bool = False
    last_advancement_revision: int = Field(ge=0)
