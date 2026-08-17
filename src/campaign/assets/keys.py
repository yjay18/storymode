"""Deterministic asset key calculation and path routing for campaign media."""

import hashlib
import json
import re

from llm.contracts.image import ImageCapability, ImagePrompt


def sanitize_filename_token(token: str) -> str:
    """Sanitize arbitrary entity tokens to safe ASCII alphanumeric and underscore characters."""
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", token).strip("_")
    return sanitized or "unnamed"


def compute_asset_key(capability: ImageCapability, prompt: ImagePrompt) -> str:
    """Compute a canonical SHA-256 content key over capability and prompt parameters."""
    canonical_payload = {
        "model_name": capability.model_name or "none",
        "model_version": capability.model_version or "none",
        "prompt_version": prompt.prompt_version,
        "style_id": prompt.style_id,
        "entity_type": prompt.entity_type,
        "entity_id": prompt.entity_id,
        "positive_prompt": prompt.positive_prompt.strip(),
        "negative_prompt": prompt.negative_prompt.strip(),
        "width": prompt.width,
        "height": prompt.height,
    }
    encoded = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_asset_relative_path(
    asset_key: str,
    entity_type: str,
    extension: str = "png",
) -> str:
    """Compute engine-owned relative storage destination for a verified asset."""
    safe_ext = extension.lstrip(".").lower()
    if safe_ext not in {"png", "jpg", "jpeg", "webp"}:
        safe_ext = "png"

    safe_type = sanitize_filename_token(entity_type)
    return f"assets/{safe_type}s/{asset_key}.{safe_ext}"
