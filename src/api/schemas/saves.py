"""Save API schemas."""

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.common import EntityId, StrictModel


class CreateSaveRequest(StrictModel):
    """Request payload to create a new character and save."""

    campaign_id: EntityId
    slot_kind: str = "manual"
    slot_name: str
    player_name: str
    background_id: EntityId
    stats: dict[str, int]
    difficulty: str = "normal"
    command_id: EntityId
    campaign_fingerprint: str | None = None


class SaveSummaryResponse(StrictModel):
    """Response payload after creating or loading a save."""

    save_id: EntityId
    campaign_id: EntityId
    revision: int
    player_name: str
    difficulty: DefaultDifficulty
    current_area_id: EntityId
    slot_name: str
    slot_kind: str
