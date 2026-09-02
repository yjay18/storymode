# Implementation Deviations

This file tracks any deviations from the original `IMPLEMENTATION_CHECKLIST.md` or design documents that occur during development. Whenever an instruction is modified, a dependency prevents exact compliance, or a technical hurdle requires a different approach, it must be recorded here.

## Milestone 1D

### ACTION-06 — Use-case location and extra files

**Original spec:** `src/engine/actions/use_cases.py` + `tests/integration/actions/test_exploration_pipeline.py`

**Deviation:** An additional `src/use_cases/exploration.py` and `tests/unit/use_cases/test_exploration.py` were created in a prior session at a non-spec path. These were kept for regression coverage and updated to point at the canonical `engine.actions.use_cases.ExplorationUseCases`, but they are not the primary ACTION-06 deliverables.

**Reason:** Prior session implemented the use case at the wrong path before the checklist spec was fully read. The deviation is now harmless as both files import from the canonical location.

### ACTION-01 / ACTION-04 — Architecture boundary (engine → llm)

**Original spec:** `tests/unit/test_architecture_imports.py` enforces that `engine` cannot import `llm`. `ActionProposal` and `EntityMention` from `llm.contracts.action` were imported directly in `engine/actions/checks.py` and `engine/actions/resolver.py` in the ACTION-01 and ACTION-04 slices.

**Deviation:** A new `src/engine/actions/protocols.py` module was created with `ActionProposalLike` and `EntityMentionLike` structural Protocols. All three engine action modules (`checks.py`, `resolver.py`, `use_cases.py`) now depend on the protocol instead of the concrete `llm` type, restoring clean boundaries.

**Reason:** `ActionProposal` was placed in `llm.contracts` per LLMCON-01, but the engine also needed to inspect proposal fields. The Protocol approach avoids moving the concrete type to `domain` (which would require a schema migration) while satisfying the boundary rule.

## Post-v1.0.0 (2026-09-02)

### Book import shipped without a checklist slice

**Original spec:** BUILD-02 covered the importer and compactor only. Every change must map to a slice and land with its design note.

**Deviation:** Commits `1c9b858` and `9dbf024` added the import CLI, the `/builder/drafts/import` route, the UI drop zone, and codex injection into stage prompts, with no ADR and with a generated `.drafts/draft-1cf4056e/draft.json` committed.

**Resolution:** ADR-012 records the decision retroactively, `docs/ux/builder-ui.md` describes the drop zone, `.drafts/` is now gitignored, and the tracked draft was removed.

### LLM adapters were never wired into the running server

**Original spec:** API-04 and LLM-09 describe `app.state.action_interpreter`, `narrator_orchestrator`, and `opportunity_planner` as the production adapters; every test injected them by hand.

**Deviation:** `create_app` never constructed them, so a real `uvicorn` server answered every free-text action with `503 interpreter_not_configured` and no test caught it because none runs the ASGI lifespan.

**Resolution:** `lifespan` now builds the adapters from `Settings` (`model_text`, `ollama_timeout_seconds`) on startup. Tests still construct the app without lifespan, so the 503 path remains covered. The builder route likewise ignored `model_text` and used the hard-coded `llama3.1:8b`; it now reads settings.

### Agent context files are tracked

**Original spec:** Root `AGENT.md` requires reading every ancestor `CONTEXT.md`/`AGENT.md` before a slice, yet `.gitignore` excluded all of them, so a fresh clone could not follow the process.

**Resolution:** The ignore rules were removed and the files committed.

### Stage prompts 2-6 described a schema that does not exist

**Original spec:** BUILD-05 promised versioned templates per stage whose JSON shape matches the BUILD-04 contracts, and BUILD-06 an orchestrator that passes stable IDs between stages.

**Deviation:** The world, areas, plot, characters, and skills templates hand-wrote shapes (`lore`, `faction_id`, `character_id`, `difficulty_scalers`) that never matched `WorldFile`, `AreasFile`, and so on, and no stage received the IDs earlier stages produced. Every generation run with a real model failed at stage 2 regardless of model size; the orchestrator tests passed because their mocks returned contract-shaped JSON directly.

**Resolution:** The stage runner now appends, from the Pydantic contracts themselves, a JSON skeleton, the field limits, and an index of IDs defined by earlier stages (plus ids referenced but not yet defined). The five templates were reduced to role, rules, and the quoted brief. Chat requests use a 16k context window and disable model thinking. Live evidence (2026-09-02, `qwen3.5:9b`, Apple Silicon): stages 1-5 (meta/style, world, areas, plot, characters) validate on the first attempt. Stage 6 (skills + items + enemies + balance in one response) still fails: two attempts were cut off mid-JSON around 1,600 lines, and the third used `""` where nullable ids must be `null`. The skeleton now renders optional scalars as `null`; the remaining fix is to split stage 6 into three responses, which is a checklist slice of its own. Until then the bundled `campaigns/salt-ledger` pack is hand-authored and validated by the same loader. Resume the evidence run with `make generate` or `scripts/generate_campaign.py --draft <id>`.

### Live model evidence

**Original spec:** No slice ran a prompt against a real model; all 577 tests use `httpx.MockTransport`.

**Resolution:** `tests/live/` holds opt-in tests gated by `STORYMODE_LIVE_OLLAMA=1` and the `live_ollama` marker. CI does not run them. `scripts/generate_campaign.py` produces the bundled sample campaign through the real pipeline.
