# Contract Test Agent Rules

- Every public contract gets smallest/full valid plus missing/extra/type/version/bound cases.
- Assert the intended stable error code and JSON pointer for invalid fixtures.
- Regenerate snapshots only through the canonical script and review semantic diffs.
- Do not weaken `extra="forbid"` or accept Markdown/prose around model JSON.
