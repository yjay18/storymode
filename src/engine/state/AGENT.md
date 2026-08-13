# State Engine Agent Rules

- Every mutation has `command_id` and `expected_revision`; replay never redraws.
- Validate complete next state/events/rolls before asking a repository to commit.
- Keep migrations pure, sequential, version-specific, and non-destructive.
- Test stale/conflicting/identical commands, receipt bounds, and unchanged input.
- Do not import concrete storage paths or narration/model adapters.
