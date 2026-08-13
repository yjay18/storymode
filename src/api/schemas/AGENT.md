# API Schemas Agent Rules

- Forbid extras and bound every user-controlled string/list/body.
- Keep domain models separate; map explicitly at route/use-case boundaries.
- Do not accept client-computed DCs, dice, effects, damage, rewards, clock/relationship/XP
  deltas, trusted proposals, or publication fingerprints.
- Add request/response/OpenAPI contract tests and maintain backward compatibility policy.
