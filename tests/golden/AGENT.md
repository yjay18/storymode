# Golden Test Agent Rules

- Update only with the owning contract/version slice and explain the semantic diff.
- Never overwrite the last fixture for a supported old schema version.
- Normalize volatile fields before comparison rather than accepting broad snapshots.
- Prompt goldens assert sections/authority/contract, not exact creative narration.
