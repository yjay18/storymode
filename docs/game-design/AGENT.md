# Game Design Agent Rules

- Keep terminology aligned with schema enum and field names.
- For every mechanic, state trigger, inputs, exact calculation/rounding, output,
  state mutation, audit event, and failure behavior.
- Do not hide balancing logic in prompts or UI code.
- A rules change requires engine unit tests and any affected fixture/schema update.
- Preserve campaign momentum: core clues cannot be destroyed by a failed check.
- Do not introduce world-time simulation, attack rolls, armour class, free-text
  combat, procedural major canon, or hidden dice manipulation in v1.
