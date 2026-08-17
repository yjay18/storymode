"""Pydantic schemas for campaign media assets and fallback descriptors."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from campaign.assets.fallback import FallbackCardDescriptor


class AssetStatusResponse(BaseModel):
    """Status and presentation descriptor for a requested campaign media asset."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_type: Literal["cover", "area_background", "enemy_portrait"]
    entity_id: str
    status: Literal["cached", "fallback", "generating", "failed"]
    image_url: str | None = None
    content_type: str | None = None
    accessible_alt: str
    fallback_card: FallbackCardDescriptor | None = None
