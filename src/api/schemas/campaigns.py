"""Campaign API schemas."""

from domain.models.campaign_meta import CampaignLength, CampaignStatus
from domain.models.character import BackgroundDefinition
from domain.models.common import EntityId, StrictModel
from domain.models.diagnostics import Diagnostic


class CampaignSummary(StrictModel):
    """Summary representation of a campaign."""

    campaign_id: EntityId
    title: str
    description: str
    version: str
    status: CampaignStatus
    campaign_length: CampaignLength
    content_fingerprint: str | None = None


class CampaignDetail(StrictModel):
    """Detailed campaign information."""

    campaign_id: EntityId
    title: str
    description: str
    version: str
    status: CampaignStatus
    campaign_length: CampaignLength
    content_fingerprint: str | None = None
    backgrounds: list[BackgroundDefinition]
    area_count: int
    has_valid_point_buy: bool


class CampaignValidationResponse(StrictModel):
    """Validation report for a campaign."""

    campaign_id: EntityId
    is_valid: bool
    diagnostics: list[Diagnostic]
