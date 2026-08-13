# Campaign Generation Prompt Specification

## Role

Generate one typed draft campaign artifact per request from the normalized user brief,
source summary, style bible, and only the earlier artifacts that it references. The
role designs content but cannot publish, calculate trusted balance, or bypass review.

## Stages and input scope

1. `meta_style`: brief/source -> draft meta and style bible.
2. `world`: brief + style -> world/factions/major locations.
3. `characters`: world + requested protagonist/companions -> character artifact.
4. `areas`: world + major character placement -> area artifact.
5. `mechanics`: world/style + explicit balance bounds -> skills/items/enemies.
6. `plot`: all stable IDs/summaries -> milestones/opportunities/clocks.
7. `art`: style + area/enemy summaries -> art prompts only.

Split an oversized stage by a deterministic ID range and merge only after independent
schema validation. Never ask the model to regenerate valid unrelated artifacts to fix
one broken reference.

## Required instruction rubric

- Use readable core skill labels and world-specific descriptions.
- Put local residents/objects in areas and only recurring major characters in the
  character artifact.
- Give items/enemies material, faction, economy, and provenance grounding.
- Preserve user-selected theme, tone, length, difficulty, and protected source facts.
- Plot milestones state canonical truth, forbidden changes, fail-forward required
  outcomes, and at least one valid next route.
- Do not introduce cloud/runtime requirements, executable formulas, raw source
  passages, or prose pretending to be validated mechanics.

## Repair

Return stable JSON-pointer diagnostics to the owning stage. The repair prompt includes
only the invalid artifact, diagnostics, and referenced summaries required to correct
it. Maximum two design repair attempts after the original; then require user review.
