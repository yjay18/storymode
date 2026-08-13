"""Area, resident, object, and encounter campaign models."""

import enum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from domain.models.common import DisplayString, EntityId, FrozenModel, SemanticVersion


class Availability(enum.StrEnum):
    """Availability status for residents and companions."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    HIDDEN = "hidden"
    DEAD = "dead"


class ResidentNpc(FrozenModel):
    """A resident NPC found in an area."""

    id: EntityId
    name: DisplayString
    role: DisplayString
    faction_id: EntityId | None = None
    availability: Availability
    location_anchor: DisplayString
    initial_disposition: Annotated[int, Field(ge=-100, le=100)]
    knowledge_tags: list[DisplayString]
    personal_goal: DisplayString
    interaction_hooks: list[DisplayString]


class AreaObject(FrozenModel):
    """An interactable object in an area."""

    id: EntityId
    name: DisplayString
    description: DisplayString
    location_anchor: DisplayString
    state: DisplayString
    interactable_tags: list[DisplayString]
    capability_requirements: list[DisplayString]
    allowed_effect_ids: list[EntityId]


class EncounterEntry(FrozenModel):
    """A combat encounter definition for an area."""

    id: EntityId
    enemy_archetype_ids: list[EntityId]
    condition: DisplayString
    weight: Annotated[int, Field(ge=1, le=100)]
    escape_policy_id: EntityId
    consequence_ids: list[EntityId]


class AreaSecret(FrozenModel):
    """A secret or clue hidden in an area."""

    id: EntityId
    summary: DisplayString
    lead_fact_ids: list[EntityId]
    reveal_conditions: list[DisplayString]
    core_clue: bool

    @model_validator(mode="after")
    def check_core_clue(self) -> "AreaSecret":
        """Core clues must have at least one lead and reveal condition."""
        if self.core_clue:
            if not self.lead_fact_ids:
                raise ValueError("core clue must have at least one lead_fact_id")
            if not self.reveal_conditions:
                raise ValueError("core clue must have at least one reveal_condition")
        return self


class AreaDefinition(FrozenModel):
    """An area or zone within the campaign world."""

    id: EntityId
    name: DisplayString
    major_location_id: EntityId
    description: DisplayString
    art_prompt: DisplayString
    danger_level: Annotated[int, Field(ge=1, le=10)]
    connected_area_ids: list[EntityId]
    local_faction_ids: list[EntityId]
    residents: list[ResidentNpc]
    objects: list[AreaObject]
    encounters: list[EncounterEntry]
    secrets: list[AreaSecret]

    @model_validator(mode="after")
    def check_connections_and_ids(self) -> "AreaDefinition":
        """Connections cannot self-reference, and local entity IDs must be unique."""
        if self.id in self.connected_area_ids:
            raise ValueError("area cannot connect to itself")
        if len(self.connected_area_ids) != len(set(self.connected_area_ids)):
            raise ValueError("duplicate area connections found")

        local_ids = []
        for r in self.residents:
            local_ids.append(r.id)
        for o in self.objects:
            local_ids.append(o.id)
        for e in self.encounters:
            local_ids.append(e.id)
        for s in self.secrets:
            local_ids.append(s.id)

        if len(local_ids) != len(set(local_ids)):
            raise ValueError("duplicate local entity IDs found within area")

        return self


class AreasFile(FrozenModel):
    """The root areas file structure."""

    schema_version: Literal[1] = 1
    campaign_id: EntityId
    campaign_version: SemanticVersion
    areas: list[AreaDefinition] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def check_global_ids(self) -> "AreasFile":
        """Resident, object, encounter, and secret IDs must be globally unique."""
        all_ids = []
        for area in self.areas:
            all_ids.append(area.id)
            for r in area.residents:
                all_ids.append(r.id)
            for o in area.objects:
                all_ids.append(o.id)
            for e in area.encounters:
                all_ids.append(e.id)
            for s in area.secrets:
                all_ids.append(s.id)

        if len(all_ids) != len(set(all_ids)):
            raise ValueError("duplicate entity IDs found across areas")

        return self
