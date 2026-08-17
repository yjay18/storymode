"""Prompt builders assembling canonical image generation prompts from campaign artifacts."""

from llm.contracts.image import ImagePrompt


def build_cover_prompt(
    campaign_id: str,
    campaign_title: str,
    tone: str,
    visual_style: str,
    motifs: list[str] | None = None,
) -> ImagePrompt:
    """Assemble a canonical cover art generation prompt for a campaign pack."""
    motifs_str = ", ".join(motifs) if motifs else "epic fantasy atmosphere"
    positive = (
        f"Masterpiece fantasy cover illustration for '{campaign_title}'. "
        f"Atmosphere: {tone}. Art direction: {visual_style}. Key visual motifs: {motifs_str}. "
        "Dynamic high-contrast composition, dramatic lighting, rich textures, award-winning art."
    )
    negative = (
        "text, typography, watermark, signature, UI elements, "
        "low resolution, blurry, distorted anatomy"
    )

    return ImagePrompt(
        style_id="default_style",
        entity_type="cover",
        entity_id=campaign_id,
        positive_prompt=positive,
        negative_prompt=negative,
        width=768,
        height=512,
    )


def build_area_background_prompt(
    area_id: str,
    area_name: str,
    area_description: str,
    style_id: str,
    visual_style: str,
    lighting_motifs: list[str] | None = None,
) -> ImagePrompt:
    """Assemble a canonical environment background illustration prompt for an exploration area."""
    lighting = (
        ", ".join(lighting_motifs) if lighting_motifs else "atmospheric environmental lighting"
    )
    positive = (
        f"Scenic environment background of {area_name}. {area_description}. "
        f"Art style: {visual_style}. Lighting: {lighting}. Wide landscape angle, "
        "immersive environmental storytelling, uncluttered center, fantasy game background."
    )
    negative = (
        "human figures in foreground, readable text, signs, logos, "
        "character portraits, watermark, UI frame"
    )

    return ImagePrompt(
        style_id=style_id,
        entity_type="area_background",
        entity_id=area_id,
        positive_prompt=positive,
        negative_prompt=negative,
        width=768,
        height=512,
    )


def build_enemy_portrait_prompt(
    enemy_id: str,
    enemy_name: str,
    archetype: str,
    visual_description: str,
    style_id: str,
    visual_style: str,
) -> ImagePrompt:
    """Assemble a canonical tactical character portrait prompt for an enemy or NPC archetype."""
    positive = (
        f"Character portrait of {enemy_name}, a {archetype}. {visual_description}. "
        f"Art style: {visual_style}. Bust framing, dark neutral background, strong silhouette, "
        "expressive fantasy concept art, high detail."
    )
    negative = (
        "complex background, landscape, full body, multiple characters, text, UI elements, blurry"
    )

    return ImagePrompt(
        style_id=style_id,
        entity_type="enemy_portrait",
        entity_id=enemy_id,
        positive_prompt=positive,
        negative_prompt=negative,
        width=512,
        height=512,
    )
