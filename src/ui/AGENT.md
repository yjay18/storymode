# UI Agent Rules

- Do not duplicate game formulas or infer allowed actions; render API results.
- Keep a mutation command ID stable across retries and reconcile unknown outcomes by
  querying server state/status before another command.
- Every component implements loading, empty, error, disabled, and success states and
  meets `docs/ux/accessibility.md` in the same slice.
- Use strict TypeScript without `any`; validate network responses at the boundary if
  the chosen generated-client approach does not provide runtime validation.
- Test user behavior, keyboard/focus, and API-result rendering—not internal component
  implementation. Run lint, typecheck, Vitest, and production build.
