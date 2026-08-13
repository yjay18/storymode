"""Plot, opportunity, and clock campaign models."""

import enum
from typing import Annotated, Literal

from pydantic import Field

from domain.models.common import DisplayString, EntityId, FrozenModel, SemanticVersion


class ClockVisibility(enum.StrEnum):
    """Visibility of a threat clock."""

    PUBLIC = "public"
    HIDDEN = "hidden"


class ClockDefinition(FrozenModel):
    """A threat or progression clock."""

    id: EntityId
    name: DisplayString
    maximum: Annotated[int, Field(ge=3, le=12)]
    visibility: ClockVisibility
    trigger_event_types: list[DisplayString]
    completion_effect_ids: list[EntityId]


class MilestoneDefinition(FrozenModel):
    """A major plot node."""

    id: EntityId
    canonical_truth: DisplayString
    narrative_purpose: DisplayString
    required_outcome_ids: list[EntityId]
    allowed_approach_tags: list[DisplayString]
    forbidden_changes: list[DisplayString]
    preconditions: list[DisplayString]
    valid_next_milestone_ids: list[EntityId]
    difficulty_band: DisplayString
    pacing_weight: Annotated[int, Field(ge=1, le=100)]
    cycle_allowed: bool


class OpportunityDefinition(FrozenModel):
    """An authored opportunity available during a milestone."""

    id: EntityId
    parent_milestone_id: EntityId
    title: DisplayString
    description: DisplayString
    referenced_entity_ids: list[EntityId]
    allowed_outcome_ids: list[EntityId]
    preconditions: list[DisplayString]
    expiry_conditions: list[DisplayString]
    balance_rating: Annotated[int, Field(ge=1, le=100)]


class PlotFile(FrozenModel):
    """The root plot file structure."""

    schema_version: Literal[1] = 1
    campaign_id: EntityId
    campaign_version: SemanticVersion
    start_milestone_ids: list[EntityId] = Field(min_length=1)
    milestones: list[MilestoneDefinition]
    authored_opportunities: list[OpportunityDefinition]
    ending_milestone_ids: list[EntityId] = Field(min_length=1)
    clock_definitions: list[ClockDefinition]
