"""Enemy campaign models."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from domain.models.common import DisplayString, EntityId, FrozenModel, SemanticVersion


class LootEntry(FrozenModel):
    """A row in a loot table."""

    item_id: EntityId
    minimum_quantity: Annotated[int, Field(ge=0)]
    maximum_quantity: Annotated[int, Field(ge=0)]
    weight: Annotated[int, Field(ge=1)]

    @model_validator(mode="after")
    def check_quantities(self) -> "LootEntry":
        """Maximum quantity cannot be less than minimum quantity."""
        if self.maximum_quantity < self.minimum_quantity:
            raise ValueError("maximum_quantity cannot be less than minimum_quantity")
        return self


class EnemyArchetype(FrozenModel):
    """An enemy archetype definition."""

    id: EntityId
    name: DisplayString
    description: DisplayString
    faction_id: EntityId | None = None
    base_hp: Annotated[int, Field(ge=1, le=10000)]
    base_armour: Annotated[int, Field(ge=0, le=10000)]
    speed: Annotated[int, Field(ge=0, le=100)]
    dexterity: Annotated[int, Field(ge=1, le=30)]
    base_mana: Annotated[int, Field(ge=0, le=1000)]
    mana_regen: Annotated[int, Field(ge=0, le=100)]
    combat_skill_ids: list[EntityId] = Field(min_length=1)
    behavior_profile: DisplayString
    escape_policy_id: EntityId
    power_rating: Annotated[int, Field(ge=1, le=10000)]
    loot_table: list[LootEntry]
    portrait_prompt: DisplayString
    art_style_ref: DisplayString


class EnemiesFile(FrozenModel):
    """The root enemies file structure."""

    schema_version: Literal[1] = 1
    campaign_id: EntityId
    campaign_version: SemanticVersion
    enemy_archetypes: list[EnemyArchetype]
