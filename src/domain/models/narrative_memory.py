"""Narrative memory limits and models."""

from typing import Literal

from pydantic import Field, model_validator

from domain.models.common import DisplayString, EntityId, FrozenModel, SemanticVersion


class NarrativeMemory(FrozenModel):
    """Memory representation for the LLM interpreter."""
    
    schema_version: Literal[1] = 1
    campaign_id: EntityId
    campaign_version: SemanticVersion
    save_id: EntityId
    
    derived_from_revision: int = Field(ge=0)
    
    recent_events: list[DisplayString] = Field(min_length=3, max_length=5)
    current_objective: DisplayString
    
    relationship_summaries: dict[EntityId, DisplayString] = Field(default_factory=dict)
    unresolved_thread_ids_summaries: dict[EntityId, DisplayString] = Field(default_factory=dict)
    active_threat_ids_summaries: dict[EntityId, DisplayString] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_size(self) -> "NarrativeMemory":
        """Bound narrative memory to 32 KiB when serialized to JSON."""
        # A quick check for 32 KiB size limit. 
        # Using model_dump_json for accurate byte length.
        json_bytes = self.model_dump_json().encode("utf-8")
        if len(json_bytes) > 32768:
            raise ValueError(f"narrative memory exceeds 32 KiB (size={len(json_bytes)} bytes)")
        return self
