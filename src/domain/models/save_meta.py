"""Save metadata models."""

import datetime
from typing import Literal

from pydantic import Field, model_validator

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.common import DisplayString, EntityId, FrozenModel, SemanticVersion


class SaveMeta(FrozenModel):
    """Display metadata for a save slot."""
    
    schema_version: Literal[1] = 1
    campaign_id: EntityId
    campaign_version: SemanticVersion
    save_id: EntityId
    
    derived_from_revision: int = Field(ge=0)
    
    slot_kind: DisplayString
    slot_name: DisplayString
    
    player_display_name: DisplayString
    player_level: int = Field(ge=1)
    
    campaign_title: DisplayString
    current_area_display_name: DisplayString
    difficulty: DefaultDifficulty
    
    play_seconds: int = Field(default=0, ge=0)
    
    created_at: datetime.datetime
    updated_at: datetime.datetime
    
    recovery_status: DisplayString

    @model_validator(mode="after")
    def check_utc(self) -> "SaveMeta":
        if self.created_at.tzinfo is None or self.created_at.tzinfo.utcoffset(self.created_at) is None:
            raise ValueError("created_at must be UTC")
        if self.updated_at.tzinfo is None or self.updated_at.tzinfo.utcoffset(self.updated_at) is None:
            raise ValueError("updated_at must be UTC")
        return self
