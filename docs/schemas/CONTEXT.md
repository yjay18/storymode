# Schema Context

This folder defines serialized contracts before code. Pydantic v2 models are the
executable source; generated JSON Schema snapshots must match these documents. v1
uses integer `schema_version = 1` at every persisted root and JSONL row.

Unknown fields and unknown enum values are errors. Stable IDs are never inferred
from display names. Cross-file references are validated after individual files parse.
