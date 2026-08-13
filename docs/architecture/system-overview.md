# System Overview

## Runtime shape

Storymode v1 is one local application process plus a local browser and an optional
Ollama process. FastAPI serves the API and, after a production build, static UI
assets. Development may run Vite separately, but both servers bind loopback only.

```text
React UI
   | typed HTTP commands/results
FastAPI transport (`src/api`)
   | application commands
Composition/application layer (`src/app`)
   | orchestrates ports
Deterministic engine (`src/engine`) ---> pure domain (`src/domain`)
   | campaign/save ports                   ^
Campaign/storage adapters (`src/campaign`) |
   |
   +-- bounded prompt request --> Ollama adapter (`src/llm`)
                                  returns untrusted proposal/prose
```

Dependency direction points toward pure domain contracts. `domain` imports only the
standard library and Pydantic contract primitives. `engine` imports `domain` and
port protocols. Concrete filesystem, Ollama, HTTP, and UI adapters depend inward;
the engine never imports those adapters.

## Modules and owners

- `app`: composition root, settings, lifespan, and concrete dependency wiring.
- `domain`: value objects, aggregate models, events, typed errors, and pure rules.
- `engine`: action, combat, progression, plot, validation, dice, and persistence
  workflows. It is the only gameplay state-transition authority.
- `campaign`: immutable pack loading/validation, builder stages, imports, generated
  assets, and filesystem repositories.
- `llm`: Ollama transport, strict proposal contracts, prompt templates, context
  retrieval, response parsing, retry policy, and deterministic fallbacks.
- `api`: local transport schemas and route adapters; no mechanics.
- `ui`: presentation and user commands; never computes authoritative outcomes.

## Core domain conventions

- IDs are lowercase, namespaced strings matching `^[a-z][a-z0-9_-]{2,63}$` and are
  never display names. References use IDs only after interpretation.
- Persisted models set `extra="forbid"`; unknown fields fail validation.
- Every persisted root carries `schema_version`; every save also carries
  `campaign_id`, `campaign_version`, `campaign_fingerprint`, `save_id`, and
  monotonic `revision`.
- All quantities use integers unless a documented multiplier is applied with an
  explicit rounding rule. HP, armour, mana, XP, ranks, and clocks never become
  negative unless the schema explicitly permits it.
- Use timezone-aware UTC timestamps only for audit metadata, never world mechanics.
- Domain errors are typed codes plus safe parameters. UI prose is mapped outside
  deterministic rules.

## Command and event model

UI/API input becomes a typed command with `save_id`, `expected_revision`, and a
unique `command_id`. The engine loads a validated snapshot, rejects stale revisions,
checks idempotency, evaluates pure rules, and returns a transition containing:

- next authoritative state;
- domain events and any roll records;
- safe result DTO data;
- optional narration facts, never narration itself.

The repository commits the transition. Only a successful commit may trigger the
narrator. Repeating a committed `command_id` returns its prior result without a new
roll or state change.

The event journal is an audit trail, not the sole source of truth. `state.json` is
the authoritative snapshot. This avoids requiring full event replay while keeping
debuggable factual history.

## State machines

Exploration actions use `submitted -> rejected | awaiting_roll | committed`. A
pending roll stores a validated immutable check specification in state; it does not
store model prose. Combat uses `inactive -> active -> resolved`, with a turn phase
and an explicit allowed-command set. Opportunity nodes and milestones use enums
defined in the schema documents. Invalid transitions return typed errors and do not
write state.

## Failure behavior

- Invalid user/LLM input: typed rejection; no mutation and no roll.
- Ollama unavailable during interpretation: report local-model unavailable; no
  mutation. Never route to cloud.
- Ollama unavailable after a committed resolution: show deterministic fallback
  result text; keep the committed result.
- Narrator invents facts or malformed output: discard it and use fallback text.
- Save revision conflict: return conflict plus current revision; never auto-replay a
  roll-bearing command.
- Corrupt/unsupported persisted data: preserve files, refuse normal load, and offer
  validation/recovery diagnostics. Never silently coerce authoritative state.

## Deferred boundaries

Desktop packaging, mod execution, multiplayer, authentication, remote hosting,
real-time world clocks, a vector store, automated companion AI, and arbitrary combat
text are outside v1. Their absence must not be anticipated with unused abstractions.
