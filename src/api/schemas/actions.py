"""Action request and response schemas."""

from domain.models.check_state import PendingCheck
from domain.models.common import EntityId, StrictModel


class SubmitActionRequest(StrictModel):
    """Request to submit a player action."""

    campaign_id: EntityId
    save_id: EntityId
    command_id: EntityId
    expected_revision: int
    player_text: str


class SubmitActionResponse(StrictModel):
    """Response after submitting an exploration action."""

    save_id: EntityId
    campaign_id: EntityId
    revision: int
    has_pending_check: bool
    rejection_reason: str | None = None
    pending_check: PendingCheck | None = None


class ResolveCheckRequest(StrictModel):
    """Request to resolve an active pending check."""

    campaign_id: EntityId
    save_id: EntityId
    command_id: EntityId
    expected_revision: int
    use_luck: bool = False


class ResolveCheckResponse(StrictModel):
    """Response after resolving a check."""

    save_id: EntityId
    campaign_id: EntityId
    revision: int
    roll: int
    band: str


class CancelCheckRequest(StrictModel):
    """Request to cancel an active pending check."""

    campaign_id: EntityId
    save_id: EntityId
    command_id: EntityId
    expected_revision: int


class CancelCheckResponse(StrictModel):
    """Response after cancelling a check."""

    save_id: EntityId
    campaign_id: EntityId
    revision: int
