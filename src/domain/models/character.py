"""Character, companion, and background campaign models."""

import enum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from domain.models.common import DisplayString, EntityId, FrozenModel, SemanticVersion


class StatName(enum.StrEnum):
    """The six core statistics."""

    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    INTELLIGENCE = "intelligence"
    CHARISMA = "charisma"
    CONSTITUTION = "constitution"
    WISDOM = "wisdom"


StatValue = Annotated[int, Field(ge=1, le=30)]


class StatBlock(FrozenModel):
    """Exact six statistics for a character."""

    strength: StatValue
    dexterity: StatValue
    intelligence: StatValue
    charisma: StatValue
    constitution: StatValue
    wisdom: StatValue


class BackgroundDefinition(FrozenModel):
    """A selectable protagonist background."""

    id: EntityId
    name: DisplayString
    description: DisplayString
    stat_bonus: StatName
    stat_bonus_value: Annotated[int, Field(ge=1, le=2)]
    starting_skill_ids: list[EntityId]
    starting_item_ids: list[EntityId]
    starting_fact_ids: list[EntityId]


class MajorNpcDefinition(FrozenModel):
    """A major NPC with persistence beyond a single area."""

    id: EntityId
    name: DisplayString
    role: DisplayString
    faction_id: EntityId | None = None
    home_area_id: EntityId
    knowledge_tags: list[DisplayString]
    goal: DisplayString
    interaction_hooks: list[DisplayString]


class CompanionDefinition(MajorNpcDefinition):
    """A recruitable companion extending major NPC data."""

    combat_role: DisplayString
    base_stats: StatBlock
    skill_tree_id: EntityId
    starting_skill_ids: list[EntityId]
    starting_loadout: list[EntityId]
    relationship_rules: list[DisplayString]
    story_hook_ids: list[EntityId]
    availability_rules: list[DisplayString]
    minimum_usable_actions: Annotated[int, Field(ge=1, le=4)]

    @model_validator(mode="after")
    def check_loadout(self) -> "CompanionDefinition":
        """Loadout must be unique, max 4, and a subset of starting skills."""
        if len(self.starting_loadout) > 4:
            raise ValueError("loadout cannot exceed four skills")
        if len(self.starting_loadout) != len(set(self.starting_loadout)):
            raise ValueError("loadout contains duplicate skills")

        known = set(self.starting_skill_ids)
        for skill_id in self.starting_loadout:
            if skill_id not in known:
                raise ValueError(f"loadout skill {skill_id} is not known")
        return self


class CharactersFile(FrozenModel):
    """The root characters file structure."""

    schema_version: Literal[1] = 1
    campaign_id: EntityId
    campaign_version: SemanticVersion
    protagonist_backgrounds: list[BackgroundDefinition]
    major_npcs: list[MajorNpcDefinition]
    companions: list[CompanionDefinition]

    @model_validator(mode="after")
    def check_unique_ids(self) -> "CharactersFile":
        """All character and background IDs must be unique within the file."""
        all_ids = []
        for bg in self.protagonist_backgrounds:
            all_ids.append(bg.id)
        for npc in self.major_npcs:
            all_ids.append(npc.id)
        for comp in self.companions:
            all_ids.append(comp.id)

        if len(all_ids) != len(set(all_ids)):
            raise ValueError("duplicate character IDs found")

        return self
