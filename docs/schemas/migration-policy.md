# Migration Policy

## Versioning

Campaign and save schemas use independent positive integer versions. Prompt contracts
and prompts have their own versions. Application semantic version does not substitute
for a data schema version.

- Additive optional fields with safe explicit defaults may remain in the same schema
  only before a published release consumes that version.
- After release, any persisted shape or semantic reinterpretation increments version.
- Removing/renaming fields, changing units/ranges/default meaning, IDs, graph semantics,
  or enum values is breaking.

Unknown newer versions fail with `unsupported_schema_version`. They are never loaded
as the latest known model.

## Migration implementation

Each step is a pure typed transformation named `migrate_vN_to_vN_plus_1`. It accepts
parsed JSON-like data for exactly version N, returns exactly N+1, and performs no I/O,
randomness, clock reads, model calls, logging side effects, or campaign mutation.

The runner:

1. validates source with its frozen old-version model/schema;
2. copies the complete save/campaign to a uniquely named backup;
3. applies one sequential step at a time and validates each output;
4. validates all cross-file invariants and bound campaign fingerprint policy;
5. writes a new sibling staging directory and syncs files;
6. installs it atomically/recoverably, retaining backup and report;
7. never deletes the only source copy.

If a step cannot infer required data without changing gameplay meaning, stop and ask
the user for an explicit choice through a migration UI/CLI option. Do not invent data.

## Tests and fixtures

Keep minimal golden fixtures for every supported version. Each migration requires:

- success from oldest supported version through current;
- idempotency guard (current version is not migrated again);
- source object/file remains unchanged;
- unknown newer and invalid source rejection;
- failure at each step preserves source and backup;
- post-migration schema/reference/invariant validation;
- explicit assertions for every changed field and semantic default.

Support policy is all versions created before v1 release during development; after
release, support at least the latest two persisted schema versions unless an ADR and
release note state a longer policy.

## Campaign fingerprint changes

A save never silently rebinds to changed campaign content. A campaign update declares
one of: compatible (old fingerprint allowlisted with proof), requires save migration,
or new campaign only. A content edit without version/fingerprint update is corruption.
