# Domain Agent Rules

- Imports are limited to standard library and Pydantic. Architecture tests enforce it.
- Follow documented names, enums, ranges, and `extra="forbid"` exactly.
- Prefer frozen value models; state transition code constructs a validated new state
  instead of mutating a loaded object in place.
- Pure rules accept every input explicitly and return typed values/errors. No I/O,
  random draw, current clock, global config, or narration.
- Test smallest valid value, every boundary, all invariant failures, and no input
  mutation. Update schema snapshots and schema docs with public model changes.
