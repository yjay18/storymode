"""Campaign asset management, deterministic keys, prompt generation, and fallback cards."""

from campaign.assets.cache import (
    AssetCache,
    AssetSidecarMetadata,
    AssetValidationError,
    detect_image_mime,
    parse_image_dimensions,
)
from campaign.assets.keys import compute_asset_key, compute_asset_relative_path
from campaign.assets.prompts import (
    build_area_background_prompt,
    build_cover_prompt,
    build_enemy_portrait_prompt,
)
from campaign.assets.queue import AssetGenerationQueue

__all__ = [
    "AssetCache",
    "AssetGenerationQueue",
    "AssetSidecarMetadata",
    "AssetValidationError",
    "build_area_background_prompt",
    "build_cover_prompt",
    "build_enemy_portrait_prompt",
    "compute_asset_key",
    "compute_asset_relative_path",
    "detect_image_mime",
    "parse_image_dimensions",
]
