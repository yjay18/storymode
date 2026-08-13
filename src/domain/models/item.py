"""Item campaign models."""

import enum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from domain.models.common import DisplayString, EntityId, FrozenModel, SemanticVersion
from domain.models.skill import EffectDefinition


class ItemType(enum.StrEnum):
    """The allowed types of items."""

    WEAPON = "weapon"
    ARMOUR = "armour"
    CONSUMABLE = "consumable"
    TOOL = "tool"
    CATALYST = "catalyst"
    QUEST = "quest"
    ACCESSORY = "accessory"


class ItemRarity(enum.StrEnum):
    """The allowed item rarities."""

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EXCEPTIONAL = "exceptional"
    UNIQUE = "unique"


class ItemDefinition(FrozenModel):
    """An item definition."""

    id: EntityId
    name: DisplayString
    type: ItemType
    rarity: ItemRarity
    mechanics: list[EffectDefinition]
    requirements: list[DisplayString]
    capability_tags: list[DisplayString]
    stacking_key: DisplayString | None = None
    flavour_text: Annotated[str, Field(min_length=1, max_length=400)]
    provenance: DisplayString
    max_stack: Annotated[int, Field(ge=1)]

    @model_validator(mode="after")
    def check_unique_stack(self) -> "ItemDefinition":
        """Unique items must have a max stack of exactly 1."""
        if self.rarity == ItemRarity.UNIQUE and self.max_stack != 1:
            raise ValueError("unique items must have max_stack=1")
        return self


class ItemsFile(FrozenModel):
    """The root items file structure."""

    schema_version: Literal[1] = 1
    campaign_id: EntityId
    campaign_version: SemanticVersion
    items: list[ItemDefinition]
