# Unit Test Agent Rules

- Name tests by observable behavior and use parameterization for documented boundaries.
- Assert exact typed result/state/events/calls and unchanged input on rejection.
- Use scripted RNG, fixed clock/IDs, and fake ports; no real network/Ollama/repo files.
- A model test covers smallest/full valid, extras, each range, and object invariant.
