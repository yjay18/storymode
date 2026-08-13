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
