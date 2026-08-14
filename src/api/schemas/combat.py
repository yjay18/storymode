"""Combat API request and response schemas."""

from pydantic import Field

from domain.models.combat_state import CombatState
from domain.models.common import EntityId, StrictModel
from engine.combat.commands import AllowedCombatAction


class StartCombatRequest(StrictModel):
    """Request to start an authored combat encounter."""

    campaign_id: EntityId
    save_id: EntityId
    encounter_id: EntityId
    command_id: EntityId
    expected_revision: int


class UseSkillRequest(StrictModel):
    """Request to use a combat skill."""

    campaign_id: EntityId
    save_id: EntityId
    skill_id: EntityId
    target_ids: list[EntityId]
    command_id: EntityId
    expected_revision: int


class DefendRequest(StrictModel):
    """Request to take the 0-cost Defend action."""

    campaign_id: EntityId
    save_id: EntityId
    command_id: EntityId
    expected_revision: int


class FleeRequest(StrictModel):
    """Request to attempt fleeing from combat."""

    campaign_id: EntityId
    save_id: EntityId
    command_id: EntityId
    expected_revision: int


class YieldRequest(StrictModel):
    """Request to yield to the enemy."""

    campaign_id: EntityId
    save_id: EntityId
    command_id: EntityId
    expected_revision: int


class CombatViewResponse(StrictModel):
    """View of the current combat state and allowed actions."""

    save_id: EntityId
    campaign_id: EntityId
    revision: int
    combat: CombatState | None = None
    allowed_actions: list[AllowedCombatAction] = Field(default_factory=list)


class CombatResponse(StrictModel):
    """Response after executing any combat command."""

    save_id: EntityId
    campaign_id: EntityId
    revision: int
    combat: CombatState | None = None
    allowed_actions: list[AllowedCombatAction] = Field(default_factory=list)
    is_terminal: bool = False
    outcome: str | None = None
    logs: list[str] = Field(default_factory=list)
