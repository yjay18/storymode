"""Deterministic themed fallback descriptors when local image assets are absent or unavailable."""

from __future__ import annotations

import hashlib
from typing import Literal

from domain.models.common import FrozenModel


class FallbackCardDescriptor(FrozenModel):
    """Themed CSS/SVG metadata for client-rendered fallback cards."""

    entity_type: Literal["cover", "area_background", "enemy_portrait"]
    entity_id: str
    title: str
    accent_color: str
    bg_gradient_start: str
    bg_gradient_end: str
    icon_symbol: str
    accessible_description: str


# Preset color palettes for deterministic selection
THEME_PALETTES = [
    ("#4f46e5", "#1e1b4b", "#0f172a"),  # Indigo / Slate
    ("#059669", "#064e3b", "#022c22"),  # Emerald / Forest
    ("#dc2626", "#7f1d1d", "#450a0a"),  # Ruby / Dark Crimson
    ("#d97706", "#78350f", "#451a03"),  # Amber / Bronze
    ("#7c3aed", "#4c1d95", "#2e1065"),  # Violet / Arcane
    ("#0284c7", "#0c4a6e", "#082f49"),  # Sky / Cobalt
]

ENTITY_ICONS: dict[str, str] = {
    "cover": "📖",
    "area_background": "🏰",
    "enemy_portrait": "⚔️",
}


def get_fallback_card(
    entity_type: Literal["cover", "area_background", "enemy_portrait"],
    entity_id: str,
    title: str,
    style_id: str = "default",
    summary: str = "",
) -> FallbackCardDescriptor:
    """Deterministically derive a themed fallback descriptor from entity attributes."""
    combined_key = f"{style_id}:{entity_type}:{entity_id}"
    digest = hashlib.sha256(combined_key.encode("utf-8")).hexdigest()
    palette_idx = int(digest[:8], 16) % len(THEME_PALETTES)
    accent, grad_start, grad_end = THEME_PALETTES[palette_idx]

    icon = ENTITY_ICONS.get(entity_type, "🛡️")

    if summary.strip():
        alt_desc = f"{entity_type.replace('_', ' ').capitalize()} for '{title}': {summary.strip()}"
    else:
        alt_desc = f"Visual representation of {title} ({entity_type.replace('_', ' ')})"

    return FallbackCardDescriptor(
        entity_type=entity_type,
        entity_id=entity_id,
        title=title,
        accent_color=accent,
        bg_gradient_start=grad_start,
        bg_gradient_end=grad_end,
        icon_symbol=icon,
        accessible_description=alt_desc,
    )
