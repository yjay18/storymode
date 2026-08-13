# Project Context

## Product vision

Storymode is a local-first, single-player text RPG with freeform exploration and
bounded, UI-driven combat. The player explores a generated but coherent campaign,
interacts with known entities, resolves meaningful uncertainty through visible
dice checks, develops a four-skill combat loadout, and may recruit up to three
authored companions.

## Current milestone

Milestone 0 is documentation-only bootstrap. The repository currently defines the
architecture and implementation plan. It intentionally contains no runtime code,
schemas, fixtures, gameplay tests, generated campaign, or frontend application.
The next work must follow `IMPLEMENTATION_CHECKLIST.md` in order.

## Non-negotiable invariant

> The LLM proposes structured interpretations and narrates confirmed outcomes. The deterministic engine validates all world references, owns all game state, rolls all dice using secure local randomness, resolves mechanics, persists state, and only then permits narration.

## Local-only boundary

- Runtime network access is limited to loopback communication with Ollama and the
  local browser/API connection.
- No cloud LLM/image API, account, telemetry, hosted backend, or paid dependency.
- The app must remain mechanically safe when Ollama is absent or returns malformed
  output. It must never silently contact an alternative provider.
- Once dependencies and models are installed, play must work offline.

## Selected architecture

- Python 3.12+, FastAPI, Pydantic v2, and explicit dependency injection.
- A React/TypeScript/Vite local web client; FastAPI is the single local backend.
- Domain models and pure rules under `src/domain`; deterministic use cases and
  state machines under `src/engine`.
- JSON campaign design packs are immutable during play. Mutable, versioned saves
  are separate JSON/JSONL files and bind to a campaign content fingerprint.
- Ollama integrations sit behind typed ports. LLM output is always untrusted input.
- Secure OS-backed randomness uses `secrets.SystemRandom`; every actual roll is
  auditable. Tests inject a deterministic fake roller, never a seed in production.
- One process and one local filesystem in v1; no service decomposition.

The rationale and consequences are recorded in
`docs/architecture/decision-log.md`.

## Generation boundaries

Design-time generation may propose a complete campaign pack, which must pass schema,
reference, graph, and balance validation before play. Runtime generation is limited
to action proposals, narration, bounded opportunity proposals attached to existing
milestones, and non-canonical scene texture. It cannot add canonical factions,
world laws, major entities, revelations, loot, mechanics, or state mutations.

## Mode boundary

- Exploration accepts free text. A local model proposes intent; the engine resolves
  entity IDs, validates capabilities and world facts, decides whether a check is
  meaningful, rolls if required, commits state, and then requests narration.
- Combat accepts only enumerated UI commands: equipped skill, defend, contextual
  flee, or contextual yield. Skills apply their guaranteed base effect and use an
  effect die only for defined additional effects.

## Data ownership and saves

Campaign definitions own immutable canonical design. Runtime state owns mutable
facts such as stats, inventory, relationships, clocks, opportunities, encounters,
and combat. Stable IDs join those layers. Saves use optimistic revisions, a
per-save write lock, validated temporary files, `fsync`, and atomic replacement of
the authoritative `state.json`. Append-only logs carry transaction/revision IDs so
recovery can identify prepared or orphaned entries. Narration is never part of the
state transaction.

## Canonical documents

- Architecture: `docs/architecture/system-overview.md`, `data-flow.md`,
  `component-boundaries.md`, `threat-model-local-only.md`, `decision-log.md`
- Rules: all files under `docs/game-design/`
- Contracts: all files under `docs/schemas/`
- Model behavior: all files under `docs/prompts/`
- UI behavior: all files under `docs/ux/`
- Execution order: `IMPLEMENTATION_CHECKLIST.md`

If two documents conflict, the more specific canonical document wins; record the
resolution in the decision log and update both documents in the same change.

## Commands

The intended setup, checks, run, validation, and smoke commands are listed in
`README.md`. They are marked as planned until the checklist slice that creates the
corresponding code is complete.
