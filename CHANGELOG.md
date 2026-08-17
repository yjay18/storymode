# Changelog

All notable changes are recorded here. Versions follow semantic versioning.

## [1.0.0] - 2026-08-17

### Added
- **Deterministic Core Rules & Combat Engine (Milestone 1)**:
  - Cryptographically secure dice rolling via `secrets.SystemRandom` (`CORE-01`).
  - Challenge classification, dynamic DCs, and difficulty scalers (`CORE-02`).
  - Hero archetypes, point-buy attributes, and progression trees (`CORE-03`).
  - 4-skill combat loadouts and tag interaction mechanics (`CORE-04`).
  - Turn-based tactical combat state machine (`CORE-05`).
  - Clocks, opportunities, and party cohesion (`CORE-06`).
  - Immutable campaign domain models (`CORE-07`).

- **Save System, Audit Trail & Schema Tooling (Milestone 2)**:
  - Validated campaign filesystem storage (`SAVE-01`).
  - Atomic JSON runtime saves with JSONL append-only action audit trail (`SAVE-02`).
  - Save schema migration and content fingerprinting (`SAVE-03`).
  - Corrupt save diagnosis and snapshot recovery utility (`SAVE-04`).
  - Code-first JSON Schema generation for 11 core contracts (`SAVE-05`).

- **Local Ollama Integration Ports (Milestone 3)**:
  - Strict loopback Ollama client with timeouts and health check (`LLM-01`).
  - Robust JSON extractor and schema validator (`LLM-02`).
  - Bounded action interpreter context packet builder (`LLM-03`).
  - Deterministic action interpreter prompt renderer and few-shot selectors (`LLM-04`).
  - Post-commit bounded narrator context builder (`LLM-06`).
  - Narrator prompt templates with deterministic fallback text (`LLM-07`).
  - Dynamic opportunity generator (`LLM-08`).
  - In-memory mock and deterministic test harnesses (`LLM-09`).

- **FastAPI Loopback Server (Milestone 4)**:
  - Application factory with CORS origin restrictiveness (`API-01`).
  - Campaign library and metadata endpoints (`API-02`).
  - Save slot creation, listing, and state inspection routes (`API-03`).
  - Action submission and check resolution endpoints (`API-04`).
  - Tactical combat execution routes (`API-05`).
  - Party, progression, and plot overview endpoints (`API-06`).

- **Campaign Builder Pipeline & Compactor (Milestone 5)**:
  - Builder brief domain models (`BUILD-01`).
  - Bounded plain-text and ePub importers with 2-pass cultural compactor (`BUILD-02`).
  - Draft repository with atomic disk operations (`BUILD-03`).
  - 7-stage sequential generation orchestrator (`BUILD-04`).
  - Generation state machine with cancel and retry support (`BUILD-05`).
  - Structured draft inspection and targeted patch editor (`BUILD-06`).
  - Graph connectivity and content validator (`BUILD-07`).
  - Atomic campaign pack publisher (`BUILD-08`).
  - Builder draft and generation API endpoints (`BUILD-09`).

- **Local Web UI (Milestone 6)**:
  - AppShell layout, banner, and navigation (`UI-01`).
  - Campaign library with quick start and recovery access (`UI-02`).
  - Save slot manager and character creation wizard (`UI-03`).
  - Quick-prompt and guided builder forms (`UI-04`).
  - Real-time generation progress monitor (`UI-06`).
  - Exploration screen with context rail, chronicle, and action composer (`UI-07`).
  - Visible dice check panel with roll history log (`UI-08`).
  - Character status and inventory management panels (`UI-09`).
  - Tactical turn-based combat dashboard (`UI-10`).
  - Save snapshot diagnosis and rollback recovery screen (`UI-11`).
  - WCAG 2.2 AA accessibility verification (`docs/ux/accessibility-test-record.md`).

- **Local Media, Security & Polish (Milestone 7)**:
  - Deterministic SHA-256 asset keys and prompt builders (`IMAGE-01`).
  - Optional local image generation adapter with atomic cache (`IMAGE-02`).
  - Deterministic themed fallback cards and asset routes (`IMAGE-03`).
  - MediaCard visual component with SVG/CSS fallback (`IMAGE-04`).
  - Adversarial security test matrix covering path traversal, injection, and resource caps (`SEC-01`).
  - Dual-job GitHub Actions CI workflow for backend and frontend (`CI-02`).
  - Strict resource limit bounds and cancellation validation (`POLISH-01`).
  - Release checklist and canonical evidence documentation (`POLISH-02`).
