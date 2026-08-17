"""Unit tests for local image generator adapter, cache install, and queue (IMAGE-02)."""

import asyncio
from pathlib import Path

import pytest

from campaign.assets import (
    AssetCache,
    AssetGenerationQueue,
    AssetValidationError,
    build_cover_prompt,
    detect_image_mime,
    parse_image_dimensions,
)
from llm.contracts.image import ImageCapability, ImageResult
from llm.orchestration.image_generator import (
    ImageModelUnavailableError,
    LocalImageGenerator,
)

# Minimal 1x1 valid PNG binary
MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00"
    b"IEND\xaeB`\x82"
)


def test_detect_image_mime() -> None:
    """Verify MIME signature detection for PNG, JPEG, WebP."""
    assert detect_image_mime(MINIMAL_PNG) == "image/png"
    assert detect_image_mime(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00") == "image/jpeg"
    assert detect_image_mime(b"RIFF\x24\x00\x00\x00WEBPVP8 \x18\x00\x00\x00") == "image/webp"
    assert detect_image_mime(b"invalid binary text") is None


def test_parse_png_dimensions() -> None:
    """Verify PNG header dimension parsing."""
    dims = parse_image_dimensions(MINIMAL_PNG, "image/png")
    assert dims == (1, 1)


def test_asset_cache_install_and_retrieval(tmp_path: Path) -> None:
    """Verify atomic asset install, file placement, and sidecar metadata."""
    cache = AssetCache(tmp_path)
    prompt = build_cover_prompt(
        campaign_id="camp_1",
        campaign_title="Sunken Temple",
        tone="mysterious",
        visual_style="watercolor",
    )
    asset_key = "test_key_12345"

    result = cache.install_asset(asset_key, prompt, MINIMAL_PNG)
    assert isinstance(result, ImageResult)
    assert result.asset_key == asset_key
    assert result.content_type == "image/png"
    assert result.width == 1
    assert result.height == 1
    assert result.byte_size == len(MINIMAL_PNG)

    # Verify retrieval
    asset_path = cache.get_asset(asset_key, "cover")
    assert asset_path is not None
    assert asset_path.exists()
    assert asset_path.read_bytes() == MINIMAL_PNG

    # Verify sidecar
    sidecar = cache.get_sidecar(asset_key, "cover")
    assert sidecar is not None
    assert sidecar.asset_key == asset_key
    assert sidecar.entity_type == "cover"
    assert sidecar.entity_id == "camp_1"


def test_asset_cache_validations(tmp_path: Path) -> None:
    """Verify size limits and MIME spoofing are rejected."""
    cache = AssetCache(tmp_path, max_bytes=50)
    prompt = build_cover_prompt("camp_1", "Title", "tone", "style")

    # Oversized payload
    with pytest.raises(AssetValidationError, match="exceeds limit"):
        cache.install_asset("k1", prompt, MINIMAL_PNG)  # MINIMAL_PNG is > 50 bytes

    # Invalid MIME
    normal_cache = AssetCache(tmp_path)
    with pytest.raises(AssetValidationError, match="invalid or unrecognized"):
        normal_cache.install_asset("k2", prompt, b"fake payload not an image")


@pytest.mark.anyio
async def test_asset_generation_queue_deduplication() -> None:
    """Verify queue deduplicates concurrent requests for identical key."""
    queue = AssetGenerationQueue()
    call_count = 0

    async def mock_generate() -> ImageResult:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return ImageResult(
            asset_key="shared_key",
            content_type="image/png",
            width=512,
            height=512,
            byte_size=100,
            relative_path="assets/covers/shared_key.png",
        )

    # Launch two concurrent requests for same key
    res1, res2 = await asyncio.gather(
        queue.enqueue_or_join("shared_key", mock_generate),
        queue.enqueue_or_join("shared_key", mock_generate),
    )

    assert res1.asset_key == "shared_key"
    assert res2.asset_key == "shared_key"
    assert call_count == 1  # Generator was executed only once


@pytest.mark.anyio
async def test_local_image_generator_unavailable() -> None:
    """Verify generator raises typed error when capability is absent."""
    generator = LocalImageGenerator()
    prompt = build_cover_prompt("camp_1", "Title", "tone", "style")
    cap_unavailable = ImageCapability(available=False)

    with pytest.raises(ImageModelUnavailableError):
        await generator.generate_image(prompt, cap_unavailable)
