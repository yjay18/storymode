# Campaign Agent Rules

- Reject unsafe IDs/paths, symlink escapes, oversized files, duplicate keys, unknown
  fields, and incompatible versions before constructing a campaign.
- Stage generation in the documented order and retain already-valid stages.
- Publishing uses a staging directory, deterministic canonical JSON/fingerprint, and
  recoverable atomic installation; never overwrite a published campaign in place.
- Model-provided formulas/paths/filenames are data errors and never executed.
- Tests require valid/invalid fixtures, cross-reference and graph failures, publish
  interruption, fingerprint stability, and no-network deterministic validation.
