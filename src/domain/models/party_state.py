"""Party and companion runtime state models."""

import enum
from typing import Annotated

from pydantic import Field, model_validator

from domain.models.common import DisplayString, EntityId, FrozenModel
from domain.models.runtime_common import FusionRecord, KnownCombatSkill, ResourceValue


class LifeState(enum.StrEnum):
    """The life and availability state of an entity."""

    ALIVE = "alive"
    DEAD = "dead"
    INJURED = "injured"
    CAPTURED = "captured"


class CompanionRuntimeState(FrozenModel):
    """The runtime state of a companion."""

    id: EntityId
    
    hp: ResourceValue
    armour: ResourceValue
    mana: ResourceValue
    
    known_combat_skills: list[KnownCombatSkill] = Field(default_factory=list)
    combat_loadout: list[EntityId] = Field(default_factory=list)
    
    relationship_value: int = Field(default=0)
    relationship_state: DisplayString = "neutral"
    
    is_available: bool = True
    life_state: LifeState = LifeState.ALIVE
    
    story_flags: dict[EntityId, bool | int | str] = Field(default_factory=dict)
    fusion_history: list[FusionRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_companion_invariants(self) -> "CompanionRuntimeState":
        """Validate loadout and life/availability consistency."""
        known_skill_ids = [k.skill_id for k in self.known_combat_skills]
        if len(known_skill_ids) != len(set(known_skill_ids)):
            raise ValueError("known_combat_skills contains duplicate skill_ids")
            
        known_set = set(known_skill_ids)
        
        if len(self.combat_loadout) > 4:
            raise ValueError("combat_loadout cannot exceed 4 items")
            
        if len(self.combat_loadout) != len(set(self.combat_loadout)):
            raise ValueError("combat_loadout contains duplicate skill_ids")
            
        for skill_id in self.combat_loadout:
            if skill_id not in known_set:
                raise ValueError(f"combat_loadout contains unknown skill_id {skill_id}")
                
        # Contradictory dead+active/unavailable state
        if self.life_state == LifeState.DEAD and self.is_available:
            raise ValueError("a dead companion cannot be available")
            
        return self


class PartyState(FrozenModel):
    """The state of the protagonist's party."""

    protagonist_id: EntityId
    active_companion_ids: list[EntityId] = Field(default_factory=list)
    companions: dict[EntityId, CompanionRuntimeState] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_party_invariants(self) -> "PartyState":
        """Validate max three unique companions and active IDs in map."""
        if len(self.active_companion_ids) > 3:
            raise ValueError("cannot have more than 3 active companions")
            
        if len(self.active_companion_ids) != len(set(self.active_companion_ids)):
            raise ValueError("active_companion_ids contains duplicates")
            
        if self.protagonist_id in self.active_companion_ids:
            raise ValueError("protagonist cannot be in active_companion_ids")
            
        if self.protagonist_id in self.companions:
            raise ValueError("protagonist cannot be in companions dict")
            
        for comp_id in self.active_companion_ids:
            if comp_id not in self.companions:
                raise ValueError(f"active companion {comp_id} not found in companions map")
                
            comp = self.companions[comp_id]
            if not comp.is_available:
                raise ValueError(f"active companion {comp_id} must be available")
            if comp.life_state != LifeState.ALIVE:
                raise ValueError(f"active companion {comp_id} must be alive (is {comp.life_state})")

        return self
