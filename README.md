# Storymode

Storymode is a local-first, single-player, D&D-style text RPG. A deterministic
Python engine owns rules and state; local Ollama models may interpret free-text
exploration actions and narrate only outcomes the engine has already confirmed.

## Current status

This repository is in **documentation-only bootstrap**. Architecture, contracts,
folder ownership, and implementation slices are defined, but there is deliberately
no application code yet. Start with [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)
and complete one unchecked slice at a time.

## Intended stack

- Python 3.12+, FastAPI, Pydantic v2, and Uvicorn
- JSON campaign packs and versioned JSON/JSONL saves
- React, TypeScript, and Vite for the local web UI
- Ollama over its loopback HTTP API; no cloud model APIs
- `secrets.SystemRandom` for gameplay dice
- Pytest, Ruff, and mypy for backend verification
- Vitest and Testing Library for frontend verification

The initial app is a browser UI served locally. Desktop packaging is explicitly
out of scope until the vertical slice is stable.

## Prerequisites

- Python 3.12 or newer
- `uv` for Python dependency locking and commands
- Node.js 22+ with npm beginning at UI slice `UI-01`
- Ollama beginning at model slice `LLM-01` (not required for deterministic milestones)

These machine-level tools are not installed or modified by this repository bootstrap.
If one is missing, obtain user approval before changing the host environment.

## Read before editing

1. Read [CONTEXT.md](CONTEXT.md).
2. Read [AGENT.md](AGENT.md).
3. Read every `CONTEXT.md` and `AGENT.md` from the target file's ancestors.
4. Read the canonical design document named by the selected checklist slice.
5. Implement only that slice and satisfy its acceptance checks.

`AGENTS.md` exists as a tool-discovery shim and points agents to the same rules.

## Planned commands

These commands become runnable when their named checklist slices are completed.
Do not claim they currently pass in this documentation-only bootstrap.

```bash
# Install Python and development dependencies (BOOT-01)
uv sync --all-groups

# Backend checks (BOOT-02 and BOOT-03)
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest

# Run local API after API-03
uv run uvicorn app.main:create_app --factory --reload

# Validate one campaign after CAMP-08
uv run python scripts/validate_campaign.py campaigns/<campaign_id>

# Run the end-to-end smoke check after SMOKE-01
uv run python scripts/run_smoke_test.py

# Frontend commands after UI-01
npm --prefix src/ui install
npm --prefix src/ui run lint
npm --prefix src/ui run test
npm --prefix src/ui run build
```

Ollama is not required for deterministic-core milestones. It first becomes an
optional runtime dependency in Milestone 4. The game must report missing models
cleanly and must never fall back to a hosted provider.

## Repository map

- `docs/architecture/`: component boundaries, data flow, security, decisions
- `docs/game-design/`: canonical mechanics and narrative constraints
- `docs/schemas/`: campaign, save, and LLM contract specifications
- `docs/prompts/`: prompt policy and role-specific prompt contracts
- `docs/ux/`: screen behavior, states, and accessibility
- `src/domain/`: pure types, invariants, and domain events
- `src/engine/`: deterministic workflows and state transitions
- `src/llm/`: untrusted Ollama boundary and context construction
- `src/campaign/`: campaign building, validation, assets, and storage
- `src/api/`: HTTP transport only
- `src/ui/`: local React client
- `tests/`: unit, integration, contract, fixture, and golden tests

## Scope guard

No cloud APIs, accounts, telemetry, hosted databases, microservices, LangChain,
vector databases, or Docker orchestration are part of v1. Any future exception
requires an ADR before a dependency or implementation is added.
