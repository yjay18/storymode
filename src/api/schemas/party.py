"""Party API request and response schemas (PROG-05)."""

from typing import Annotated

from pydantic import Field

from domain.models.common import DisplayString, EntityId, StrictModel


class RecruitCompanionRequest(StrictModel):
    """Request to recruit a companion into the party."""

    command_id: EntityId
    expected_revision: Annotated[int, Field(ge=0)]
    companion_id: EntityId


class ActivateCompanionRequest(StrictModel):
    """Request to move a companion to the active party roster."""

    command_id: EntityId
    expected_revision: Annotated[int, Field(ge=0)]
    companion_id: EntityId


class DeactivateCompanionRequest(StrictModel):
    """Request to bench an active companion."""

    command_id: EntityId
    expected_revision: Annotated[int, Field(ge=0)]
    companion_id: EntityId


class LeaveCompanionRequest(StrictModel):
    """Request for a companion to leave the party."""

    command_id: EntityId
    expected_revision: Annotated[int, Field(ge=0)]
    companion_id: EntityId


class CompanionView(StrictModel):
    """View model for a companion."""

    id: EntityId
    name: DisplayString
    role: DisplayString
    life_state: str
    is_available: bool
    is_active: bool
    hp_current: int
    hp_maximum: int
    mana_current: int
    mana_maximum: int
    combat_loadout: list[EntityId]
    known_skill_ids: list[EntityId]


class PartyViewResponse(StrictModel):
    """Party roster view."""

    protagonist_id: EntityId
    active_companion_ids: list[EntityId]
    companions: list[CompanionView]


class PartyReceiptView(StrictModel):
    """Receipt for party command."""

    command_id: EntityId
    committed_revision: int
    result_kind: DisplayString
    safe_result_summary: DisplayString


class PartyMutationResponse(StrictModel):
    """Response returned after a party mutation."""

    save_id: EntityId
    revision: int
    receipt: PartyReceiptView
    party: PartyViewResponse
