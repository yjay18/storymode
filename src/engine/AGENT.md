# Engine Agent Rules

- Write focused tests first with fake repositories/random/clock/IDs.
- One command handler performs one atomic transition and returns typed events/effects.
- Call the roller only after all deterministic validation and only the documented
  number of times. Never catch a valid undesirable roll and retry.
- Do not import FastAPI, concrete filesystem classes, or concrete Ollama code.
- Preserve input state on rejection and assert that invariant in tests.
- Any new rule requires its game-design update; any state/event change requires schema
  update and migration analysis. Run unit plus relevant integration/contract tests.
