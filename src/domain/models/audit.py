"""Audit models (journal and roll logs)."""

import datetime
from typing import Annotated, Literal

from pydantic import Field, model_validator

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.common import DisplayString, EntityId, FrozenModel
from domain.models.skill import EffectDefinition


class JournalEvent(FrozenModel):
    """A narrative/system event appended to the journal."""
    
    schema_version: Literal[1] = 1
    event_id: EntityId
    transaction_id: EntityId
    revision: int = Field(ge=0)
    event_index: int = Field(ge=0)
    recorded_at: datetime.datetime
    
    command_id: EntityId
    event_type: DisplayString
    
    actor_ids: list[EntityId] = Field(default_factory=list)
    entity_ids: list[EntityId] = Field(default_factory=list)
    
    resolved_intent: DisplayString | None = None
    roll_ids: list[EntityId] = Field(default_factory=list)
    
    effects: list[EffectDefinition] = Field(default_factory=list)
    discovered_fact_ids: list[EntityId] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_utc(self) -> "JournalEvent":
        if self.recorded_at.tzinfo is None or self.recorded_at.tzinfo.utcoffset(self.recorded_at) is None:
            raise ValueError("recorded_at must be UTC")
        return self


class RollRecord(FrozenModel):
    """An audited die roll."""
    
    schema_version: Literal[1] = 1
    roll_id: EntityId
    transaction_id: EntityId
    revision: int = Field(ge=0)
    recorded_at: datetime.datetime
    
    command_id: EntityId
    reason: DisplayString
    die_sides: int = Field(ge=2)
    raw_rolls: list[int] = Field(min_length=1)
    selected_roll_index: int = Field(ge=0)
    
    named_modifiers: dict[DisplayString, int] = Field(default_factory=dict)
    total: int
    
    dc: int | None = None
    difficulty: DefaultDifficulty | None = None
    outcome: DisplayString | None = None
    confirmed_effect_ids: list[EntityId] = Field(default_factory=list)
    supersedes_roll_id: EntityId | None = None

    @model_validator(mode="after")
    def check_roll_bounds(self) -> "RollRecord":
        if self.recorded_at.tzinfo is None or self.recorded_at.tzinfo.utcoffset(self.recorded_at) is None:
            raise ValueError("recorded_at must be UTC")
            
        for roll in self.raw_rolls:
            if not (1 <= roll <= self.die_sides):
                raise ValueError(f"raw_roll {roll} is out of bounds for d{self.die_sides}")
                
        if self.selected_roll_index >= len(self.raw_rolls):
            raise ValueError("selected_roll_index is out of bounds")
            
        return self
