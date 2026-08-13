# LLM Retrieval Agent Rules

- Include only facts the role needs and only knowledge revealed to the acting perspective.
- Use stable ordinals/order and deterministic optional truncation.
- Fail `context_too_large` rather than truncating mandatory JSON/references.
- Test hidden-fact exclusion, hostile quoted data, budgets, and same-input determinism.
- Do not import repositories; callers provide typed snapshots/candidates.
