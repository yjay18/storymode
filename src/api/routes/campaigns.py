"""Campaign API endpoints."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.campaigns import CampaignDetail, CampaignSummary, CampaignValidationResponse
from app.config import Settings
from app.dependencies import get_settings
from domain.models.campaign_meta import CampaignMeta
from domain.models.common import EntityId
from engine.campaign import load_campaign

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _resolve_campaign_dir(settings: Settings, campaign_id: str) -> Path:
    """Safely resolve campaign directory under configured root."""
    if ".." in campaign_id or "/" in campaign_id or "\\" in campaign_id:
        raise HTTPException(status_code=404, detail="Invalid campaign ID")

    root = Path(settings.campaigns_dir).resolve()

    # Check directly under root, or under root/campaigns
    cand1 = root / campaign_id
    if cand1.is_dir() and (cand1 / "campaign.json").exists():
        return cand1

    cand2 = root / "campaigns" / campaign_id
    if cand2.is_dir() and (cand2 / "campaign.json").exists():
        return cand2

    raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found")


def _find_all_campaign_dirs(settings: Settings) -> list[Path]:
    """Find all campaign directories containing campaign.json."""
    root = Path(settings.campaigns_dir).resolve()
    dirs: list[Path] = []

    search_paths = [root]
    if (root / "campaigns").exists():
        search_paths.append(root / "campaigns")

    seen: set[str] = set()
    for base in search_paths:
        if not base.exists():
            continue
        for child in base.iterdir():
            if child.is_dir() and (child / "campaign.json").exists() and child.name not in seen:
                seen.add(child.name)
                dirs.append(child)

    return dirs


@router.get("", response_model=list[CampaignSummary])
def list_campaigns(settings: Annotated[Settings, Depends(get_settings)]) -> list[CampaignSummary]:
    """List all available campaigns."""
    summaries: list[CampaignSummary] = []

    for c_dir in _find_all_campaign_dirs(settings):
        try:
            meta_content = (c_dir / "campaign.json").read_text(encoding="utf-8")
            meta = CampaignMeta.model_validate_json(meta_content)
            summaries.append(
                CampaignSummary(
                    campaign_id=meta.campaign_id,
                    title=meta.title,
                    description=meta.source_summary,
                    version=str(meta.campaign_version),
                    status=meta.status,
                    campaign_length=meta.campaign_length,
                    content_fingerprint=meta.content_fingerprint,
                )
            )
        except Exception:
            continue

    return summaries


@router.get("/{campaign_id}", response_model=CampaignDetail)
def get_campaign(
    campaign_id: EntityId,
    settings: Annotated[Settings, Depends(get_settings)],
) -> CampaignDetail:
    """Get detailed information for a specific campaign."""
    c_dir = _resolve_campaign_dir(settings, campaign_id)
    pack, _ = load_campaign(c_dir)

    if pack is None:
        # If loading full pack failed, fallback to campaign.json meta or return 404
        try:
            meta_content = (c_dir / "campaign.json").read_text(encoding="utf-8")
            meta = CampaignMeta.model_validate_json(meta_content)
            return CampaignDetail(
                campaign_id=meta.campaign_id,
                title=meta.title,
                description=meta.source_summary,
                version=str(meta.campaign_version),
                status=meta.status,
                campaign_length=meta.campaign_length,
                content_fingerprint=meta.content_fingerprint,
                backgrounds=[],
                area_count=0,
                has_valid_point_buy=False,
            )
        except Exception:
            raise HTTPException(status_code=404, detail="Campaign could not be loaded") from None

    return CampaignDetail(
        campaign_id=pack.meta.campaign_id,
        title=pack.meta.title,
        description=pack.meta.source_summary,
        version=str(pack.meta.campaign_version),
        status=pack.meta.status,
        campaign_length=pack.meta.campaign_length,
        content_fingerprint=pack.meta.content_fingerprint,
        backgrounds=pack.characters.protagonist_backgrounds,
        area_count=len(pack.areas.areas),
        has_valid_point_buy=pack.skills.point_buy is not None,
    )


@router.get("/{campaign_id}/validation", response_model=CampaignValidationResponse)
def get_campaign_validation(
    campaign_id: EntityId,
    settings: Annotated[Settings, Depends(get_settings)],
) -> CampaignValidationResponse:
    """Validate a campaign and return diagnostic reports."""
    c_dir = _resolve_campaign_dir(settings, campaign_id)
    pack, diagnostics = load_campaign(c_dir)

    return CampaignValidationResponse(
        campaign_id=campaign_id,
        is_valid=pack is not None and not diagnostics,
        diagnostics=diagnostics,
    )
