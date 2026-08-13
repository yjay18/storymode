"""World, location, and entity override models."""

from pydantic import Field

from domain.models.common import DisplayString, EntityId, FrozenModel
from domain.models.party_state import LifeState


class LocationState(FrozenModel):
    """The current location of the party."""

    area_id: EntityId
    zone_anchor: DisplayString | None = None
    discovered_area_ids: set[EntityId] = Field(default_factory=set)


class NpcOverride(FrozenModel):
    """Runtime overrides for an NPC's baseline definition."""

    location_area_id: EntityId | None = None
    location_zone_anchor: DisplayString | None = None
    
    is_available: bool | None = None
    life_state: LifeState | None = None
    
    disposition: DisplayString | None = None
    relationship_value: int | None = None
    
    revealed_knowledge_tags: set[DisplayString] | None = None


class ObjectOverride(FrozenModel):
    """Runtime overrides for an interactive object."""

    state_enum: DisplayString | None = None
    is_discovered: bool | None = None
    quantity: int | None = None
    allowed_effect_data: dict[str, str | int | bool] | None = Field(default=None)


class WorldState(FrozenModel):
    """The state of the world, overrides, and global facts."""

    # Note: world_flags and known_fact_ids are usually at the root of state.json,
    # but Location and Overrides are sub-objects. We model them here as standalone 
    # to be composed into RuntimeState later.
    pass
