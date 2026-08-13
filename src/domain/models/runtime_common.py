"""Common models used across the runtime state."""

from pydantic import Field, model_validator

from domain.models.common import EntityId, FrozenModel


class ResourceValue(FrozenModel):
    """A tracked resource with a current value and maximum capacity."""

    current: int = Field(ge=0)
    maximum: int = Field(ge=0)

    @model_validator(mode="after")
    def check_bounds(self) -> "ResourceValue":
        """Current value cannot exceed maximum."""
        if self.current > self.maximum:
            raise ValueError(f"current ({self.current}) cannot exceed maximum ({self.maximum})")
        return self


class StatusInstance(FrozenModel):
    """An active status effect instance."""

    status_id: EntityId
    duration_remaining: int | None = Field(default=None, ge=1)
    magnitude: int | None = None
    source_entity_id: EntityId | None = None


class InventoryEntry(FrozenModel):
    """An entry in an inventory or equipment list."""

    item_id: EntityId
    quantity: int = Field(default=1, ge=1)
    instance_data: dict[str, str | int | bool] | None = None


class KnownCombatSkill(FrozenModel):
    """A combat skill known by a character."""

    skill_id: EntityId
    level: int = Field(ge=1, le=5)
    acquisition_source_id: EntityId


class FusionRecord(FrozenModel):
    """A record of a completed skill fusion."""

    recipe_id: EntityId
    source_skill_ids: list[EntityId] = Field(min_length=2, max_length=2)
    result_skill_id: EntityId
