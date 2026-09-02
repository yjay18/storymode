# Project Context

## Product vision

Storymode is a local-first, single-player text RPG with freeform exploration, rich bottom-up world-building from literature/prompts, and bounded UI-driven combat. The player explores a generated, coherent campaign, interacts with known entities, resolves meaningful uncertainty through visible dice checks, develops a four-skill combat loadout, and may recruit companions.

## Current status: v1.0.0 (Fully Implemented)

All 7 core milestones are implemented, tested, and verified:
- **Milestone 1**: Core rules, progression, and deterministic combat engine.
- **Milestone 2**: Save system, snapshot recovery, and JSON schemas.
- **Milestone 3**: Local Ollama LLM integration, bounded action interpreter, and narrator.
- **Milestone 4**: FastAPI loopback REST API server.
- **Milestone 5**: 7-stage campaign authoring pipeline, ePub/text compactor, and draft workspace.
- **Milestone 6**: Local React 19 / TypeScript 5.7 / Vite 7 user interface.
- **Milestone 7**: Local image rendering, deterministic asset keys/fallbacks, adversarial security suite, and CI automation.

## Non-negotiable invariant

> The LLM proposes structured interpretations and narrates confirmed outcomes. The deterministic engine validates all world references, owns all game state, rolls all dice using secure local randomness, resolves mechanics, persists state, and only then permits narration.

## Local-only boundary

- Runtime network access is strictly limited to loopback communication with Ollama and the local browser/API connection (`127.0.0.1` / `localhost`).
- No cloud LLM/image API, account, telemetry, hosted backend, or paid dependency.
- The app remains mechanically safe and playable when Ollama is absent or returns malformed output. It never silently contacts an alternative provider.
- Once dependencies and models are installed, play functions completely offline.

## Selected architecture

- Python 3.12+, FastAPI, Pydantic v2, and explicit dependency injection.
- A React/TypeScript/Vite local web client; FastAPI is the single local backend.
- Domain models and pure rules under `src/domain`; deterministic use cases and state machines under `src/engine`.
- JSON campaign design packs are immutable during play. Mutable, versioned saves are separate JSON/JSONL files and bind to a campaign content fingerprint.
- Ollama integrations sit behind typed ports. LLM output is always untrusted input.
- Secure OS-backed randomness uses `secrets.SystemRandom`; every actual roll is auditable. Tests inject a deterministic fake roller, never a seed in production.
- One process and one local filesystem in v1; no service decomposition.

The rationale and consequences are recorded in `docs/architecture/decision-log.md`.
