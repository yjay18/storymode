"""Pending check runtime model."""

from pydantic import Field, model_validator

from domain.models.character import StatName
from domain.models.common import DisplayString, EntityId, FrozenModel
from domain.models.skill import EffectDefinition


class CheckOutcomes(FrozenModel):
    """Allowed outcomes for each d20 band."""

    natural_1: list[EffectDefinition]
    low: list[EffectDefinition]
    standard: list[EffectDefinition]
    strong: list[EffectDefinition]
    natural_20: list[EffectDefinition]


class PendingCheck(FrozenModel):
    """An unresolved difficulty check."""

    check_id: EntityId
    source_command_id: EntityId
    source_revision: int = Field(ge=0)
    
    original_input: DisplayString
    resolved_operation: DisplayString
    actor_id: EntityId
    target_ids: list[EntityId] = Field(default_factory=list)
    
    stat: StatName | None = None
    skill_id: EntityId | None = None
    
    named_modifiers: dict[DisplayString, int] = Field(default_factory=dict)
    semantic_difficulty: DisplayString
    
    base_dc: int = Field(default=10, ge=1)
    difficulty_adjustment: int = Field(default=0)
    final_dc: int = Field(default=10, ge=1)
    
    stakes: DisplayString
    allowed_outcomes: CheckOutcomes

    @model_validator(mode="after")
    def check_arithmetic_consistency(self) -> "PendingCheck":
        """Verify that base_dc + difficulty_adjustment == final_dc."""
        if self.base_dc + self.difficulty_adjustment != self.final_dc:
            raise ValueError(
                f"Arithmetic mismatch: base_dc ({self.base_dc}) + "
                f"difficulty_adjustment ({self.difficulty_adjustment}) != "
                f"final_dc ({self.final_dc})"
            )
        return self
