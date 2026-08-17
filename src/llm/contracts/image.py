"""Pydantic schemas and typed contracts for local image generation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ImageCapability(BaseModel):
    """Local image generation availability and model capability metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    available: bool = False
    model_name: str | None = None
    model_version: str | None = None
    supported_dimensions: tuple[tuple[int, int], ...] = (
        (512, 512),
        (768, 512),
        (512, 768),
        (1024, 1024),
    )
    supported_mimes: tuple[str, ...] = ("image/png", "image/jpeg", "image/webp")
    max_bytes: int = 10 * 1024 * 1024  # 10 MB limit


class ImagePrompt(BaseModel):
    """Assembled prompt and constraints for local image rendering."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_version: str = "1.0"
    style_id: str
    entity_type: Literal["cover", "area_background", "enemy_portrait"]
    entity_id: str
    positive_prompt: str = Field(min_length=1, max_length=2000)
    negative_prompt: str = Field(default="", max_length=1000)
    width: int = 512
    height: int = 512


class ImageResult(BaseModel):
    """Metadata describing a generated and validated image asset."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    asset_key: str
    content_type: str
    width: int
    height: int
    byte_size: int
    relative_path: str
