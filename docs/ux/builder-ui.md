# Campaign Builder UI

## Shared pipeline

Guided and Quick Prompt paths produce the same normalized builder brief, staged draft
artifacts, validation report, review screens, and explicit Publish command. Quick mode
may prefill defaults but cannot skip review or validation.

## Guided inputs

Collect theme/genre, tone, original premise or local source material, target length,
difficulty, world rules, faction ideas, enemy preferences, protagonist concept,
desired readable skills/classes, major plot preferences, content boundaries, and art
direction. Each step saves a draft locally and can be revisited before generation.

Source import shows accepted types/sizes, provenance field, local-only notice, and a
plain-text preview. It never executes content or sends it outside the local process.

## Generation progress

Show the exact stage, local model, attempts, elapsed time, cancellation, and validation
diagnostics. Completed valid stages are retained; retry only the failed owning stage.
Cancel leaves an inspectable draft, never a partially published campaign.

## Review

Use separate tabs for meta/style, world/factions, characters, areas, skills, items,
enemies, plot, balance, and art. Forms edit typed fields and show JSON pointer errors.
Cross-file reference pickers use IDs plus display names and prevent unknown targets.
An advanced raw JSON view may be read-only in v1; avoiding a full schema-aware editor
keeps initial scope bounded.

## Validation and publish

Display diagnostics sorted by file/pointer/code with error vs warning. Publish is
disabled on any error and requires explicit confirmation that published design becomes
immutable for existing saves. Publishing calculates fingerprint and creates no save.
Missing optional image assets are warnings with deterministic fallback preview.
