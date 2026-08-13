# Domain Models Agent Rules

- Read the exact schema section and implement only its named models.
- Inherit the shared strict base; forbid extras and mutable collection defaults.
- Reject booleans as integers, naive timestamps, invalid IDs, and unknown versions.
- Add boundary and invalid-invariant unit tests plus schema snapshots when public.
- Do not import repositories, rules engines, HTTP, filesystem, or model adapters.
