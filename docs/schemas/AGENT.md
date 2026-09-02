# Schema Agent Rules

- Implement documented class and field names exactly; do not rename for taste.
- Persist enums as lowercase strings and timestamps as UTC RFC 3339 strings.
- Set `extra="forbid"`, validate assignment where mutable models require it, and use
  fresh default factories for collections.
- Add one smallest valid fixture and focused invalid fixtures for every constraint.
- Regenerate checked-in JSON Schemas only through the canonical generation script.
- Breaking changes require a new version, sequential migration, golden old fixture,
  docs, tests, and changelog entry.
- Do not put narrator prose, Python class names, absolute paths, or secrets in state.
