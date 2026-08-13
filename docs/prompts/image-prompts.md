# Image Prompt Specification

## Scope

Generate optional campaign cover art, area backgrounds, and enemy archetype portraits
locally. Images are presentation assets; gameplay never depends on visual analysis.

## Prompt assembly

Use campaign art direction, allowed palette/material/lighting motifs, subject/area
description, composition, aspect ratio, and negative constraints. Do not include raw
source text, hidden plot truth, player/save data, model instructions from imported
content, or filesystem paths.

Area backgrounds avoid readable text and reserve composition space for UI overlays.
Enemy portraits specify archetype, silhouette, materials, faction markings, framing,
and neutral background. Variants inherit archetype and style IDs.

## Cache key and storage

The engine computes SHA-256 over capability, local model name/version when available,
prompt version, canonical prompt, dimensions, style ID, and entity ID. Store under an
engine-selected campaign asset path with sidecar metadata. Never overwrite a different
hash. Validate MIME signature, byte size, and dimensions before installation.

## Capability and fallback

At builder/review time, check whether the configured local Ollama installation exposes
the required image capability. If absent/failing, create no fake generated file. UI
uses a deterministic themed CSS/SVG card derived from campaign palette and entity type.
Campaign validation warns about missing optional art but remains playable.
