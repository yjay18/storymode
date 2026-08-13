"""World and faction campaign models."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from domain.models.common import DisplayString, EntityId, FrozenModel, SemanticVersion


class PowerSystem(FrozenModel):
    """Rules and costs of the macro power system."""

    rules: list[DisplayString] = Field(min_length=1)
    costs: list[DisplayString] = Field(min_length=1)
    access_restrictions: list[DisplayString] = Field(min_length=1)
    side_effects: list[DisplayString] = Field(min_length=1)


class FactionRelationship(FrozenModel):
    """An edge between factions."""

    target_faction_id: EntityId
    stance: Annotated[int, Field(ge=-100, le=100)]
    summary: DisplayString


class FactionDefinition(FrozenModel):
    """A macro faction in the world."""

    id: EntityId
    name: DisplayString
    goals: list[DisplayString]
    resources: list[DisplayString]
    hypocrisy: DisplayString
    language_style: DisplayString
    visual_markings: DisplayString
    relationship_edges: list[FactionRelationship]

    @model_validator(mode="after")
    def check_relationships(self) -> "FactionDefinition":
        """Relationships must not self-reference and must have unique targets."""
        targets = set()
        for edge in self.relationship_edges:
            if edge.target_faction_id == self.id:
                raise ValueError("faction cannot have a relationship with itself")
            if edge.target_faction_id in targets:
                raise ValueError(f"duplicate relationship target: {edge.target_faction_id}")
            targets.add(edge.target_faction_id)
        return self


class MajorLocation(FrozenModel):
    """A macro location in the world."""

    id: EntityId
    name: DisplayString
    summary: DisplayString


class WorldDefinition(FrozenModel):
    """The macro structure and factions of the world."""

    name: DisplayString
    core_conflict: DisplayString
    power_system: PowerSystem
    values: list[DisplayString]
    factions: list[FactionDefinition]
    major_locations: list[MajorLocation]
    material_conditions: list[DisplayString]

    @model_validator(mode="after")
    def check_unique_ids(self) -> "WorldDefinition":
        """Factions and major locations must have unique IDs."""
        faction_ids = [f.id for f in self.factions]
        if len(faction_ids) != len(set(faction_ids)):
            raise ValueError("duplicate faction IDs found")

        location_ids = [loc.id for loc in self.major_locations]
        if len(location_ids) != len(set(location_ids)):
            raise ValueError("duplicate major location IDs found")

        return self


class WorldFile(FrozenModel):
    """The root world file structure."""

    schema_version: Literal[1] = 1
    campaign_id: EntityId
    campaign_version: SemanticVersion
    world: WorldDefinition
