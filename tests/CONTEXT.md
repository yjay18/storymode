# Test Context

Tests mirror deterministic boundaries:

- `unit/`: pure models/rules/state machines with scripted dependencies;
- `contract/`: JSON/Pydantic schemas, invalid fixtures, LLM responses, OpenAPI;
- `integration/`: filesystem repositories, command pipelines, API adapters;
- `fixtures/`: tiny versioned campaign/save JSON inputs, both valid and intentionally
  invalid with the expected diagnostic encoded in the filename/manifest;
- `golden/`: immutable old-version migration inputs and stable schema snapshots.

Normal tests make no network calls, need no Ollama, and never rely on probabilistic
outcomes or wall-clock timing.
