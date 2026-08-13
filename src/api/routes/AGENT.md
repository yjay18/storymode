# API Routes Agent Rules

- Keep handlers thin and async only when the called boundary is async.
- Apply documented HTTP mapping and safe correlation/error envelopes consistently.
- Mutation inputs require command ID/expected revision; reject unknown fields.
- Test through dependency overrides for success, rejection, stale, replay, and safe errors.
- Update OpenAPI snapshot for every public route/response change.
