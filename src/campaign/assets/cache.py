"""Validated atomic caching and retrieval for campaign media assets."""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any

from domain.models.common import FrozenModel
from llm.contracts.image import ImagePrompt, ImageResult


class AssetValidationError(Exception):
    """Raised when an asset byte payload fails MIME, size, or structural validation."""


class AssetSidecarMetadata(FrozenModel):
    """Sidecar metadata describing a cached image asset."""

    asset_key: str
    entity_type: str
    entity_id: str
    style_id: str
    content_type: str
    width: int
    height: int
    byte_size: int
    created_at_utc: str


def detect_image_mime(data: bytes) -> str | None:
    """Inspect magic header bytes to safely detect supported image MIME types."""
    if len(data) < 12:
        return None

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"

    return None


def parse_image_dimensions(data: bytes, mime: str) -> tuple[int, int] | None:
    """Parse width and height from image binary headers without external dependencies."""
    try:
        if mime == "image/png" and len(data) >= 24:
            # PNG IHDR chunk starts at byte 12; width at 16..20, height at 20..24
            width = int.from_bytes(data[16:20], "big")
            height = int.from_bytes(data[20:24], "big")
            return (width, height)
        if mime == "image/jpeg" and len(data) >= 4:
            # Basic scan for SOF0/SOF2 marker
            idx = 2
            while idx < len(data) - 9:
                if data[idx] == 0xFF:
                    marker = data[idx + 1]
                    if marker in (0xC0, 0xC1, 0xC2, 0xC3):  # SOF markers
                        height = int.from_bytes(data[idx + 5 : idx + 7], "big")
                        width = int.from_bytes(data[idx + 7 : idx + 9], "big")
                        return (width, height)
                    length = int.from_bytes(data[idx + 2 : idx + 4], "big")
                    idx += 2 + length
                else:
                    idx += 1
        if mime == "image/webp" and len(data) >= 30:
            # VP8 / VP8L chunk parsing
            if data[12:16] == b"VP8 ":
                width = int.from_bytes(data[26:28], "little") & 0x3FFF
                height = int.from_bytes(data[28:30], "little") & 0x3FFF
                return (width, height)
            if data[12:16] == b"VP8L":
                b0, b1, b2, b3 = data[21], data[22], data[23], data[24]
                width = 1 + (((b1 & 0x3F) << 8) | b0)
                height = 1 + (((b3 & 0xF) << 10) | (b2 << 2) | ((b1 & 0xC0) >> 6))
                return (width, height)
    except Exception:
        return None

    return None


class AssetCache:
    """Local-first cache storing verified campaign image assets and metadata."""

    def __init__(self, campaign_dir: Path, max_bytes: int = 10 * 1024 * 1024) -> None:
        self._campaign_dir = campaign_dir.resolve()
        self._assets_dir = (self._campaign_dir / "assets").resolve()
        self._max_bytes = max_bytes

    @property
    def assets_dir(self) -> Path:
        return self._assets_dir

    def get_asset(self, asset_key: str, entity_type: str) -> Path | None:
        """Retrieve existing cached file path if it exists and is within asset root."""
        type_dir = self._assets_dir / f"{entity_type}s"
        if not type_dir.exists():
            return None

        # Search for any valid extension
        for ext in ("png", "jpeg", "jpg", "webp"):
            candidate = (type_dir / f"{asset_key}.{ext}").resolve()
            if candidate.exists() and candidate.is_relative_to(self._assets_dir):
                return candidate

        return None

    def get_sidecar(self, asset_key: str, entity_type: str) -> AssetSidecarMetadata | None:
        """Retrieve sidecar metadata for a cached asset."""
        type_dir = self._assets_dir / f"{entity_type}s"
        sidecar_path = (type_dir / f"{asset_key}.json").resolve()
        if not sidecar_path.exists() or not sidecar_path.is_relative_to(self._assets_dir):
            return None

        try:
            with open(sidecar_path, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
            return AssetSidecarMetadata.model_validate(data)
        except Exception:
            return None

    def install_asset(
        self,
        asset_key: str,
        prompt: ImagePrompt,
        image_bytes: bytes,
    ) -> ImageResult:
        """Validate, write atomically via temp file + fsync, and register sidecar metadata."""
        if len(image_bytes) > self._max_bytes:
            raise AssetValidationError(
                f"Asset payload exceeds limit ({len(image_bytes)} > {self._max_bytes} bytes)"
            )

        detected_mime = detect_image_mime(image_bytes)
        if not detected_mime:
            raise AssetValidationError("Payload has invalid or unrecognized image MIME signature")

        dimensions = parse_image_dimensions(image_bytes, detected_mime)
        width, height = dimensions if dimensions else (prompt.width, prompt.height)

        ext = detected_mime.split("/")[-1]
        if ext == "jpeg":
            ext = "jpg"

        type_dir = self._assets_dir / f"{prompt.entity_type}s"
        type_dir.mkdir(parents=True, exist_ok=True)

        target_file = (type_dir / f"{asset_key}.{ext}").resolve()
        sidecar_file = (type_dir / f"{asset_key}.json").resolve()

        if not target_file.is_relative_to(self._assets_dir):
            raise AssetValidationError("Derived target path escapes campaign assets directory")

        # Atomic temp file write
        temp_target = type_dir / f".tmp_{asset_key}_{os.getpid()}.{ext}"
        try:
            with open(temp_target, "wb") as f:
                f.write(image_bytes)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_target, target_file)
        finally:
            if temp_target.exists():
                temp_target.unlink(missing_ok=True)

        # Write sidecar metadata
        metadata = AssetSidecarMetadata(
            asset_key=asset_key,
            entity_type=prompt.entity_type,
            entity_id=prompt.entity_id,
            style_id=prompt.style_id,
            content_type=detected_mime,
            width=width,
            height=height,
            byte_size=len(image_bytes),
            created_at_utc=datetime.datetime.now(datetime.UTC).isoformat(),
        )
        temp_sidecar = type_dir / f".tmp_{asset_key}_{os.getpid()}.json"
        try:
            with open(temp_sidecar, "w", encoding="utf-8") as f:
                f.write(metadata.model_dump_json(indent=2))
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_sidecar, sidecar_file)
        finally:
            if temp_sidecar.exists():
                temp_sidecar.unlink(missing_ok=True)

        rel_path = str(target_file.relative_to(self._campaign_dir))

        return ImageResult(
            asset_key=asset_key,
            content_type=detected_mime,
            width=width,
            height=height,
            byte_size=len(image_bytes),
            relative_path=rel_path,
        )
