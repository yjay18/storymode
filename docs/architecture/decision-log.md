# Architecture Decision Log

Decisions are append-only. Superseded entries remain and link to their replacement.
Status values are `Accepted`, `Superseded`, or `Proposed`.

## ADR-001 — Deterministic engine owns state and outcomes

- **Date:** 2026-08-12
- **Status:** Accepted
- **Decision:** The LLM may return typed proposals and prose only. The engine resolves
  references, rules, random results, state transitions, and persistence.
- **Context:** Free text benefits from language models, but mechanics and continuity
  must be fair, auditable, and recoverable.
- **Consequences:** Model output is always validated. Narration happens after commit.
  More explicit contracts and fallback text are required.
- **Alternatives rejected:** LLM-authored state patches; prompt-only rule enforcement;
  model-generated dice.
- **Affected modules/docs/tests:** `domain`, `engine`, `llm`; system overview, LLM
  contracts; action/combat/LLM contract tests.

## ADR-002 — Local Ollama is the only model provider

- **Date:** 2026-08-12
- **Status:** Accepted
- **Decision:** Text and optional image generation use a loopback Ollama adapter with
  capability checks. There is no hosted fallback.
- **Context:** The product must be local-first, free after installation, private, and
  offline-capable.
- **Consequences:** Users manage models locally; model absence is a normal typed state;
  deterministic fallback presentation is required after committed outcomes.
- **Alternatives rejected:** Cloud APIs; multi-provider abstraction in v1; embedded
  model runtimes maintained by the app.
- **Affected modules/docs/tests:** `llm`, app settings, threat model; health, timeout,
  redirect, and unavailable-model tests.

## ADR-003 — Immutable JSON campaign packs and separate JSON/JSONL saves

- **Date:** 2026-08-12
- **Status:** Accepted
- **Decision:** Published design files are immutable and content-fingerprinted. Mutable
  state is stored under distinct save directories in versioned JSON/JSONL files.
- **Context:** Campaigns should be portable and editable before publish, while runtime
  facts need migrations and must not rewrite canonical design.
- **Consequences:** Stable IDs and cross-file validation are mandatory. Saves bind to
  a campaign fingerprint. Multi-file logs need revision-aware recovery.
- **Alternatives rejected:** One mutable world JSON; database-only storage; event
  sourcing as the sole state representation.
- **Affected modules/docs/tests:** `campaign`, `engine/state`, schema docs; fingerprint,
  load, migration, round-trip, corruption, and recovery tests.

## ADR-004 — Freeform exploration and UI-bounded combat are separate modes

- **Date:** 2026-08-12
- **Status:** Accepted
- **Decision:** Exploration may use free text and a typed interpreter proposal. Combat
  accepts only engine-advertised enumerated commands.
- **Context:** Expressive world interaction is valuable outside combat; deterministic,
  readable tactical pacing is more important during combat.
- **Consequences:** Two explicit state machines and UI surfaces are required. The
  action parser is not callable while combat is active.
- **Alternatives rejected:** Free text in combat; menus-only exploration; a single
  universal action grammar.
- **Affected modules/docs/tests:** action/combat engines, API routes, UX; mode guard and
  allowed-command tests.

## ADR-005 — Secure randomness with complete roll audit

- **Date:** 2026-08-12
- **Status:** Accepted
- **Decision:** Production uses `secrets.SystemRandom`. One injected `RandomSource`
  supplies rolls, and every actual roll receives an ID and revision-tagged audit row.
- **Context:** Fairness must not be influenced by narrative or reproducible seeding.
- **Consequences:** Tests use scripted fakes. Production rolls cannot be replayed from
  seeds; idempotent command handling prevents duplicate rolls.
- **Alternatives rejected:** `random.Random`; LLM randomness; hidden pity systems;
  retrying undesirable results.
- **Affected modules/docs/tests:** `engine/dice`, action/combat resolution, roll schema;
  boundary, audit, idempotency, and statistical-range tests (not distribution tests).

## ADR-006 — Campaign spine plus bounded mutable opportunity frontier

- **Date:** 2026-08-12
- **Status:** Accepted
- **Decision:** Protected milestone truth provides coherence. Runtime opportunities
  form a 3–7 node frontier and must attach to existing milestones/entities.
- **Context:** A rigid tree is brittle, while unconstrained runtime invention causes
  canonical drift.
- **Consequences:** Opportunity proposals need reference/graph/balance validation and
  explicit active/deferred/locked/invalidated/resolved states.
- **Alternatives rejected:** Fixed branch tree; deleting every unchosen path; allowing
  runtime generation to rewrite milestone truth.
- **Affected modules/docs/tests:** `engine/plot`, builder, LLM planner; graph, pruning,
  protected-truth, expiry, and frontier-bound tests.

## ADR-007 — Bounded skill progression and authored fusion

- **Date:** 2026-08-12
- **Status:** Accepted
- **Decision:** Characters know discoverable skills, equip at most four, upgrade combat
  skills through levels 1–5, and fuse only authored compatible level-5 pairs at an
  unlocked specialist/location with a catalyst. Companion fusions unlock a defined
  backup skill.
- **Context:** Build variety should come from tactical function, not uncontrolled
  numeric inflation or model invention.
- **Consequences:** Every upgrade/fusion is data-defined, reference-validated, atomic,
  and covered by invariants preventing under-equipped companions.
- **Alternatives rejected:** Procedural runtime fusion; unrestricted respecs; pure
  damage multiplication; more than four equipped skills.
- **Affected modules/docs/tests:** progression, skills schema, combat UI; prerequisite,
  consumption, slot, balance, and companion-safeguard tests.

## ADR-008 — Modular monolith with local React web UI

- **Date:** 2026-08-12
- **Status:** Accepted
- **Decision:** Use one Python modular monolith with FastAPI and a React/TypeScript/Vite
  client. Serve the built client from the local app; use Vite separately in development.
- **Context:** A solo, agent-assisted project benefits from explicit boundaries without
  deployment complexity.
- **Consequences:** Modules enforce dependency rules in tests. API DTOs are distinct
  from domain types. Desktop packaging is deferred.
- **Alternatives rejected:** Microservices; Electron/Tauri in the first slice; server-
  rendered templates; a Python-only desktop toolkit.
- **Affected modules/docs/tests:** all modules, UI, CI; architecture import tests and
  API/UI contract tests.

## ADR-009 — Pydantic-first contracts and explicit version migrations

- **Date:** 2026-08-12
- **Status:** Accepted
- **Decision:** Pydantic v2 models are executable contracts and emit checked-in JSON
  Schemas. Persisted roots use integer schema versions; unsupported versions fail.
- **Context:** Multiple agents and model-generated data require one strict source for
  validation and clear compatibility behavior.
- **Consequences:** Unknown fields are forbidden. Schema snapshots and invalid fixtures
  are tests. Breaking changes require pure sequential migrations.
- **Alternatives rejected:** Ad hoc dictionaries; JSON Schema maintained independently;
  permissive unknown-field loading.
- **Affected modules/docs/tests:** domain models, contracts, fixtures, migration script;
  schema snapshot and migration golden tests.

## ADR-010 — Revisioned snapshot commit with prepared append-only records

- **Date:** 2026-08-12
- **Status:** Accepted
- **Decision:** `state.json` is the authoritative atomic commit point. Under a per-save
  lock, revision-tagged journal/roll records are prepared and synced before a validated
  temporary state atomically replaces it. Derived files may be rebuilt.
- **Context:** Portable JSON/JSONL cannot provide a native multi-file transaction, yet
  state must be atomic and rolls/events auditable across crashes.
- **Consequences:** Load/recovery ignores or marks records newer than authoritative
  revision, command IDs are idempotent, and platform-specific directory sync is tested
  where possible.
- **Alternatives rejected:** Non-atomic direct writes; SQLite as authoritative storage;
  treating narrative output as part of commit.
- **Affected modules/docs/tests:** state repository, save schema, recovery script;
  interruption-at-each-step, stale revision, duplicate command, and round-trip tests.

## ADR-011 — Explicit initial dependencies only

- **Date:** 2026-08-12
- **Status:** Accepted
- **Decision:** Initial Python runtime dependencies are FastAPI, Uvicorn, Pydantic,
  pydantic-settings, and HTTPX. Development uses Pytest, Ruff, and mypy. Frontend uses
  React, TypeScript, Vite, Vitest, and Testing Library when UI bootstrap begins.
- **Context:** Each dependency must provide a concrete capability while keeping local
  setup and agent reasoning small.
- **Consequences:** No ORM, queue, framework for LLM chains, vector database, or general
  utility package. Lockfiles are committed when dependencies are first installed.
- **Alternatives rejected:** Large application frameworks; dependency-free HTTP/schema
  implementations; preemptive libraries without a current slice.
- **Affected modules/docs/tests:** `pyproject.toml`, future UI package files, README, CI.

## ADR-012 — Imported books are a campaign source, not campaign content

- **Date:** 2026-09-02
- **Status:** Accepted (retroactive; shipped after v1.0.0 without a checklist slice)
- **Decision:** A local EPUB or plain-text book may seed a builder draft. The importer
  chunks the text, the two-pass compactor distills a bounded `WorldCodex` (cultural
  profiles, key characters, primary areas), and every generation stage receives that
  codex as quoted context alongside the brief. Book text never reaches the engine, a
  save, or a prompt as instructions. Entry points are `scripts/import_book.py`, the
  `POST /api/v1/builder/drafts/import` route, and the web builder's drop zone.
- **Context:** BUILD-02 specified the importer and compactor; the CLI, API route, UI, and
  stage-prompt injection were added afterwards to make "turn this novel into a campaign"
  a one-step flow. Builder drafts under `.drafts/` are local work-in-progress and are not
  tracked; only published packs under `campaigns/` are.
- **Consequences:** The codex is bounded by the same context budgets as other prompts.
  Faithfulness to the book is best-effort; the published pack is still validated by the
  same schema and graph checks as a prompt-only campaign. Imported text is treated as
  untrusted data in the threat model.
- **Alternatives rejected:** Retrieval over the full book at play time (violates the
  bounded-context rule and the immutable-pack rule); letting the model author pack files
  directly from raw chapters (unbounded prompts, no cultural synthesis).
- **Affected modules/docs/tests:** `src/campaign/importers/`, `src/llm/prompts/campaign_generation_v1.py`,
  `src/campaign/generation/orchestrator.py`, `src/api/routes/builder.py`,
  `src/ui/src/features/builder/BookImportDropzone.tsx`, `docs/ux/builder-ui.md`,
  `tests/integration/campaign/test_book_import_cli_and_compactor.py`,
  `tests/integration/api/test_builder_routes.py`.
