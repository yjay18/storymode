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


class FusionRecipeView(StrictModel):
    """An authored fusion recipe and whether the protagonist can perform it now."""

    recipe_id: EntityId
    source_skill_ids: list[EntityId]
    result_skill_id: EntityId
    catalyst_item_id: EntityId
    catalyst_quantity: int
    blocked_reason: str | None
    """The first unmet prerequisite, or null when the recipe is eligible."""


class FusionRecipeListResponse(StrictModel):
    """Every authored fusion recipe, with eligibility evaluated against this save."""

    save_id: EntityId
    revision: int
    recipes: list[FusionRecipeView]


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
    xp_for_next_level: int | None
    """Authored total XP at which the next level triggers; null at the top level."""

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
