"""FastAPI routes serving campaign media assets and deterministic fallback descriptors."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from api.schemas.assets import AssetStatusResponse
from campaign.assets.cache import AssetCache
from campaign.assets.fallback import get_fallback_card

router = APIRouter(prefix="/api/v1/campaigns/{campaign_id}/assets", tags=["assets"])


def _get_campaign_dir(campaign_id: str) -> Path:
    """Resolve and validate campaign pack directory."""
    clean_id = campaign_id.strip()
    if not clean_id or ".." in clean_id or "/" in clean_id or "\\" in clean_id:
        raise HTTPException(status_code=400, detail="Invalid campaign ID")

    campaigns_root = Path("campaigns").resolve()
    campaign_dir = (campaigns_root / clean_id).resolve()
    if not campaign_dir.is_relative_to(campaigns_root):
        raise HTTPException(status_code=400, detail="Campaign path escapes campaigns directory")

    return campaign_dir


@router.get(
    "/{entity_type}/{entity_id}",
    response_model=AssetStatusResponse,
)
async def get_asset_descriptor(
    campaign_id: str,
    entity_type: Literal["cover", "area_background", "enemy_portrait"],
    entity_id: str,
) -> AssetStatusResponse:
    """Retrieve asset status: cached URL if generated locally, or deterministic fallback card."""
    campaign_dir = _get_campaign_dir(campaign_id)
    cache = AssetCache(campaign_dir)

    # Check for existing cached file for this entity
    # Search for sidecars matching entity_id in this type's directory
    type_dir = cache.assets_dir / f"{entity_type}s"
    cached_key: str | None = None
    content_type: str | None = None

    if type_dir.exists():
        for sidecar_path in type_dir.glob("*.json"):
            sidecar = cache.get_sidecar(sidecar_path.stem, entity_type)
            if sidecar and sidecar.entity_id == entity_id:
                cached_key = sidecar.asset_key
                content_type = sidecar.content_type
                break

    fallback_desc = get_fallback_card(
        entity_type=entity_type,
        entity_id=entity_id,
        title=entity_id.replace("_", " ").title(),
    )

    if cached_key and content_type:
        raw_url = f"/api/v1/campaigns/{campaign_id}/assets/{entity_type}/{entity_id}/raw"
        return AssetStatusResponse(
            entity_type=entity_type,
            entity_id=entity_id,
            status="cached",
            image_url=raw_url,
            content_type=content_type,
            accessible_alt=fallback_desc.accessible_description,
            fallback_card=None,
        )

    return AssetStatusResponse(
        entity_type=entity_type,
        entity_id=entity_id,
        status="fallback",
        image_url=None,
        content_type=None,
        accessible_alt=fallback_desc.accessible_description,
        fallback_card=fallback_desc,
    )


@router.get(
    "/{entity_type}/{entity_id}/raw",
)
async def get_asset_raw_bytes(
    campaign_id: str,
    entity_type: Literal["cover", "area_background", "enemy_portrait"],
    entity_id: str,
) -> Response:
    """Stream raw image binary bytes with security headers."""
    campaign_dir = _get_campaign_dir(campaign_id)
    cache = AssetCache(campaign_dir)

    type_dir = cache.assets_dir / f"{entity_type}s"
    if not type_dir.exists():
        raise HTTPException(status_code=404, detail="Asset not found")

    target_file: Path | None = None
    content_type: str = "image/png"

    for sidecar_path in type_dir.glob("*.json"):
        sidecar = cache.get_sidecar(sidecar_path.stem, entity_type)
        if sidecar and sidecar.entity_id == entity_id:
            asset_file = cache.get_asset(sidecar.asset_key, entity_type)
            if asset_file and asset_file.exists():
                target_file = asset_file
                content_type = sidecar.content_type
                break

    if not target_file:
        raise HTTPException(status_code=404, detail="Asset not found")

    headers = {
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox",
        "Cache-Control": "public, max-age=86400, immutable",
    }

    return FileResponse(
        path=target_file,
        media_type=content_type,
        headers=headers,
    )
