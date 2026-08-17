# Storymode v1.0.0 Release Checklist & Evidence

This document contains canonical verification evidence across all 7 milestones of Storymode.

## Release Metadata
- **Version**: `1.0.0`
- **Release Date**: 2026-08-17
- **Target Platform**: macOS (Darwin / Apple Silicon), Linux (x86_64 / arm64)
- **Local Engine**: Python 3.12+ (FastAPI + Pydantic v2 + Uvicorn)
- **Local UI**: React 19 + TypeScript 5.7 + Vite 7

---

## 1. Automated Quality Gate Evidence

### 1.1 Backend Quality Gates
```bash
uv run python scripts/check_scaffold.py
uv run python scripts/generate_schemas.py --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests scripts
uv run pytest tests/ -q
uv run python scripts/run_smoke_test.py
```
- **Scaffold Check**: PASSED
- **Schema Drift Check**: PASSED (11 canonical schemas synchronized)
- **Ruff Format & Lint**: PASSED (319 files formatted, 0 linter errors)
- **Mypy Strict Type Check**: PASSED (0 errors across 283 source files)
- **Pytest Suite**: PASSED (**573 unit and integration tests passed**)
- **End-to-End Smoke Test**: PASSED (Phase 1 engine + Phase 2 ASGI exploration and combat flow)

### 1.2 Frontend UI Quality Gates
```bash
cd src/ui
npm run lint
npm run typecheck
npm run test
npm run build
```
- **ESLint**: PASSED (0 errors, 0 warnings)
- **TypeScript**: PASSED (0 errors)
- **Vitest**: PASSED (**40 component and integration tests passed** across 23 test suites)
- **Production Build**: PASSED (300.61 kB JS bundle, 2.60 kB CSS)

---

## 2. Milestone Feature Verification

| Milestone | Scope | Status | Evidence |
|---|---|---|---|
| **Milestone 1** | **Deterministic Rules & Engine Core** | Verified | Core dice roller with `secrets.SystemRandom`, difficulty adjustment, hero progression, 4-skill combat loadout, turn-based combat engine, opportunity resolution, and immutable campaign models (`CORE-01` to `CORE-07`). |
| **Milestone 2** | **State, Saves & Schema Contracts** | Verified | Campaign JSON validation, versioned runtime saves, JSONL append-only audit trail, crash-safe atomic snapshot recovery, and 11 generated JSON Schemas (`SAVE-01` to `SAVE-05`). |
| **Milestone 3** | **Local Ollama Integration Ports** | Verified | Loopback health inspection, structured JSON parser with schema validation, bounded action interpreter, deterministic prompt renderer, narrator post-commit adapter, and opportunity planner (`LLM-01` to `LLM-09`). |
| **Milestone 4** | **FastAPI Server & Endpoints** | Verified | Loopback ASGI server, error envelopes with UUID command IDs, save/character/action/combat/party/plot routes (`API-01` to `API-06`). |
| **Milestone 5** | **Authoring Pipeline & Compactor** | Verified | Plain-text and ePub chunking/parsing, 2-pass cultural profile compactor, 7-stage generation orchestrator, draft repository, review edits, validation report, atomic publisher, and builder routes (`BUILD-01` to `BUILD-09`). |
| **Milestone 6** | **Local React 19 UI** | Verified | AppShell, Campaign Library, Guided/Quick Builder forms, Generation Progress, Exploration screen with context rail and chronicle, visible dice check panel, character/inventory panels, tactical combat interface, and save recovery utility (`UI-01` to `UI-11`). |
| **Milestone 7** | **Local Media & Security Polish** | Verified | Deterministic asset keys, local image generation adapter, validated atomic asset cache, fallback descriptors, MediaCard component, adversarial security test suite, GitHub Actions CI workflow, and resource bounds (`IMAGE-01` to `POLISH-02`). |

---

## 3. Threat Model & Security Compliance

- **No Remote Calls**: Confirmed zero non-loopback network calls. No cloud API keys or telemetry.
- **Strict Loopback Binding**: Ollama calls verified strictly for `http://127.0.0.1` and `http://localhost`.
- **Directory Traversal**: Comprehensive tests in `tests/integration/security/` prove resistance to `..`, absolute paths, symlinks, and URL-encoded escapes.
- **Prompt Injection Containment**: Player free text and imported book contents are treated purely as quoted data within prompt contracts; all game state transitions are authoritatively validated and committed by the deterministic engine.
- **Fail-Safe Offline Mode**: Missing or unreachable local Ollama instances gracefully degrade to deterministic fallback narration and themed SVG/CSS visual cards without interrupting gameplay.
