# Storymode

Storymode is a local-first, single-player, D&D-style text RPG engine and companion web app. A deterministic Python engine authoritatively owns rules and game state; optional local Ollama models interpret natural language exploration actions, assist campaign generation, and narrate outcomes only after the engine has validated and committed them.

## Current Status: v1.0.0 (Complete)

All 7 milestones (`CORE`, `SAVE`, `LLM`, `API`, `BUILD`, `UI`, `IMAGE/SEC/POLISH`) are fully implemented and verified against the canonical design specifications.

## Technology Stack

- **Engine Core**: Python 3.12+, FastAPI, Pydantic v2, and Uvicorn
- **Deterministic Mechanics**: `secrets.SystemRandom` OS-backed cryptographically secure dice roller
- **Campaign & Save Storage**: Content-fingerprinted JSON campaign packs and atomic versioned JSON/JSONL saves
- **Local AI Integration**: Loopback HTTP communication with local Ollama (`llama3`, `mistral`, `sdxl-turbo`); zero cloud APIs or telemetry
- **Web UI**: React 19, TypeScript 5.7, Vite 7, and WCAG 2.2 AA accessibility
- **Quality Assurance**: 570+ Pytest tests, strict Mypy type-checking, Ruff, Vitest, and automated security test suite

---

## Quickstart

### 1. Prerequisites
- Python 3.12+ and `uv`
- Node.js 22+ and `npm`
- (Optional) Local [Ollama](https://ollama.com) instance running on `http://127.0.0.1:11434`

### 2. Install Dependencies
```bash
# Install Python backend dependencies
uv sync --all-groups

# Install React UI dependencies
cd src/ui
npm install
cd ../..
```

### 3. Run Verification Quality Gates
```bash
# Backend checks (lint, format, types, unit/integration/security tests, smoke test)
uv run python scripts/check_scaffold.py
uv run python scripts/generate_schemas.py --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests scripts
uv run pytest tests/ -q
uv run python scripts/run_smoke_test.py

# Frontend checks (ESLint, TypeScript typecheck, Vitest, production build)
cd src/ui
npm run lint
npm run typecheck
npm run test
npm run build
cd ../..
```

### 4. Start the Application

#### Start the Backend API Server:
```bash
uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```
Interactive OpenAPI documentation will be accessible at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

#### Start the React Frontend:
```bash
cd src/ui
npm run dev
```
Navigate to [http://localhost:5173](http://localhost:5173) in your browser.

---

## Architecture Invariants

> **Core Invariant**: The LLM proposes structured interpretations and narrates confirmed outcomes. The deterministic engine validates all world references, owns all game state, rolls all dice using secure local randomness, resolves mechanics, persists state, and only then permits narration.

- **Local-First & Private**: Zero external cloud API calls, zero telemetry, and zero remote data leakage.
- **Fail-Safe Operation**: Missing or unresponsive local models automatically fall back to deterministic gameplay cards, structured choices, and themed visual fallback descriptors.
- **Immutability & Integrity**: Campaign packs are immutable during gameplay. Saves record complete deterministic event audit trails with atomic snapshot rollback recovery.

---

## Documentation

- [Implementation Checklist](IMPLEMENTATION_CHECKLIST.md): Complete milestone and slice specification
- [Release Checklist & Evidence](docs/release-checklist.md): Verification report across all milestones
- [Accessibility Test Record](docs/ux/accessibility-test-record.md): WCAG 2.2 AA manual and automated test matrix
- [Architecture Threat Model](docs/architecture/threat-model-local-only.md): Local-only security boundary and containment
