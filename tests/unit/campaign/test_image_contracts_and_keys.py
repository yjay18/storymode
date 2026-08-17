"""Unit tests for image contracts, prompt builders, and deterministic asset keys (IMAGE-01)."""

import pytest
from pydantic import ValidationError

from campaign.assets import (
    build_area_background_prompt,
    build_cover_prompt,
    build_enemy_portrait_prompt,
    compute_asset_key,
    compute_asset_relative_path,
)
from llm.contracts.image import ImageCapability, ImagePrompt, ImageResult


def test_image_contracts_validation() -> None:
    """Verify pydantic contracts enforce strict constraints and forbid extra keys."""
    cap = ImageCapability(available=True, model_name="sdxl-turbo")
    assert cap.available is True
    assert cap.model_name == "sdxl-turbo"

    with pytest.raises(ValidationError):
        # extra field forbidden
        ImageCapability(available=True, unknown_field="invalid")  # type: ignore[call-arg]

    prompt = ImagePrompt(
        style_id="dark_fantasy",
        entity_type="cover",
        entity_id="campaign_1",
        positive_prompt="A glowing obsidian fortress on a storm-lashed cliff.",
    )
    assert prompt.width == 512
    assert prompt.height == 512

    with pytest.raises(ValidationError):
        # empty prompt violates min_length
        ImagePrompt(
            style_id="dark_fantasy",
            entity_type="cover",
            entity_id="campaign_1",
            positive_prompt="",
        )


def test_asset_key_stability_and_sensitivity() -> None:
    """Verify compute_asset_key is deterministic and sensitive to all parameters."""
    cap1 = ImageCapability(available=True, model_name="sdxl-turbo", model_version="1.0")
    cap2 = ImageCapability(available=True, model_name="sdxl-turbo", model_version="1.0")

    prompt1 = build_cover_prompt(
        campaign_id="citadel",
        campaign_title="Iron Citadel",
        tone="grimdark",
        visual_style="oil painting",
        motifs=["stone", "rain"],
    )
    prompt2 = build_cover_prompt(
        campaign_id="citadel",
        campaign_title="Iron Citadel",
        tone="grimdark",
        visual_style="oil painting",
        motifs=["stone", "rain"],
    )

    key1 = compute_asset_key(cap1, prompt1)
    key2 = compute_asset_key(cap2, prompt2)

    assert key1 == key2
    assert len(key1) == 64  # SHA-256 hex string

    # Change model name
    cap_diff_model = ImageCapability(available=True, model_name="stable-diffusion-3")
    assert compute_asset_key(cap_diff_model, prompt1) != key1

    # Change title in prompt
    prompt_diff_title = build_cover_prompt(
        campaign_id="citadel",
        campaign_title="Golden Citadel",
        tone="grimdark",
        visual_style="oil painting",
    )
    assert compute_asset_key(cap1, prompt_diff_title) != key1

    # Change dimensions
    prompt_diff_dims = prompt1.model_copy(update={"width": 1024})
    assert compute_asset_key(cap1, prompt_diff_dims) != key1


def test_asset_relative_path_safety() -> None:
    """Verify compute_asset_relative_path creates safe engine-owned relative destinations."""
    key = "a" * 64
    path = compute_asset_relative_path(key, "cover", "png")
    assert path == f"assets/covers/{key}.png"

    # Directory traversal or unsafe chars in entity_type are sanitized
    unsafe_path = compute_asset_relative_path(key, "../../../etc/passwd", "png")
    assert ".." not in unsafe_path
    assert unsafe_path.startswith("assets/")

    # Unsupported extension falls back to png
    bad_ext_path = compute_asset_relative_path(key, "enemy_portrait", "exe")
    assert bad_ext_path == f"assets/enemy_portraits/{key}.png"


def test_prompt_builders_structure() -> None:
    """Verify prompt builders assemble valid positive and negative constraints."""
    bg_prompt = build_area_background_prompt(
        area_id="forbidden_crypt",
        area_name="Forbidden Crypt",
        area_description="Dusty stone sarcophagi illuminated by blue phantom flames.",
        style_id="gothic_ruins",
        visual_style="charcoal concept art",
        lighting_motifs=["pale blue flames"],
    )
    assert bg_prompt.entity_type == "area_background"
    assert "Forbidden Crypt" in bg_prompt.positive_prompt
    assert "human figures in foreground" in bg_prompt.negative_prompt

    portrait_prompt = build_enemy_portrait_prompt(
        enemy_id="orc_warlord",
        enemy_name="Gorgar",
        archetype="Brutal Warlord",
        visual_description="Scarred face with rusted iron battle-axe.",
        style_id="gothic_ruins",
        visual_style="charcoal concept art",
    )
    assert portrait_prompt.entity_type == "enemy_portrait"
    assert "Gorgar" in portrait_prompt.positive_prompt
    assert "dark neutral background" in portrait_prompt.positive_prompt


def test_image_result_schema() -> None:
    """Verify ImageResult contract serialization."""
    res = ImageResult(
        asset_key="abc12345",
        content_type="image/png",
        width=512,
        height=512,
        byte_size=10240,
        relative_path="assets/covers/abc12345.png",
    )
    assert res.asset_key == "abc12345"
    assert res.byte_size == 10240
