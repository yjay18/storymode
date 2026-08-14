"""Progression and skills API request and response schemas (PROG-05)."""

from typing import Annotated

from pydantic import Field

from domain.models.common import DisplayString, EntityId, StrictModel


class GrantXpRequest(StrictModel):
    """Request to grant XP to the player."""

    command_id: EntityId
    expected_revision: Annotated[int, Field(ge=0)]
    xp_amount: Annotated[int, Field(ge=1)]


class UpgradeSkillRequest(StrictModel):
    """Request to upgrade a skill."""

    command_id: EntityId
    expected_revision: Annotated[int, Field(ge=0)]
    skill_id: EntityId
    target_id: EntityId | None = None


class SetLoadoutRequest(StrictModel):
    """Request to update a 4-slot combat loadout."""

    command_id: EntityId
    expected_revision: Annotated[int, Field(ge=0)]
    loadout: list[EntityId]
    target_id: EntityId | None = None


class PerformFusionRequest(StrictModel):
    """Request to execute a skill fusion."""

    command_id: EntityId
    expected_revision: Annotated[int, Field(ge=0)]
    recipe_id: EntityId
    companion_id: EntityId | None = None


class KnownSkillView(StrictModel):
    """View model for a known skill."""

    skill_id: EntityId
    current_level: int


class InventoryItemView(StrictModel):
    """View model for an inventory entry."""

    item_id: EntityId
    quantity: int


class ProgressionReceiptView(StrictModel):
    """Receipt for progression command."""

    command_id: EntityId
    committed_revision: int
    result_kind: DisplayString
    safe_result_summary: DisplayString


class PlayerProgressionView(StrictModel):
    """Player progression status."""

    id: EntityId
    name: DisplayString
    level: int
    xp: int
    upgrade_tokens: int
    hp_current: int
    hp_maximum: int
    mana_current: int
    mana_maximum: int
    combat_loadout: list[EntityId]
    known_skills: list[KnownSkillView]
    inventory: list[InventoryItemView]


class ProgressionViewResponse(StrictModel):
    """View response for character progression."""

    save_id: EntityId
    revision: int
    player: PlayerProgressionView


class ProgressionMutationResponse(StrictModel):
    """Response returned after a progression mutation."""

    save_id: EntityId
    revision: int
    receipt: ProgressionReceiptView
    player: PlayerProgressionView
