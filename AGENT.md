# Agent Operating Manual

This file governs every repository change. Root `AGENTS.md` exists so tools that
auto-discover plural instruction files load this manual.

## Required read order

Before editing any file:

1. Read root `CONTEXT.md` and this file.
2. Select exactly one unchecked slice in `IMPLEMENTATION_CHECKLIST.md` unless the
   user explicitly selects a different bounded scope.
3. Read each ancestor folder's `CONTEXT.md` and `AGENT.md` from root to target.
4. Read every canonical document listed in the slice's **Read** field.
5. Inspect adjacent code and tests. Never infer a contract from a filename alone.

The applicable vertical chain for `src/engine/combat/resolver.py`, for example, is
root context/manual, `src/CONTEXT.md`, `src/AGENT.md`,
`src/engine/CONTEXT.md`, `src/engine/AGENT.md`, and
`docs/game-design/combat-rules.md`.

## Mandatory workflow

```text
1. Read applicable CONTEXT.md and AGENT.md files.
2. Apply the ponytail skill (YAGNI, minimal diff, reuse existing codebase/stdlib).
3. State the contract/invariants affected before editing.
4. Make the smallest coherent change.
5. Add or update tests first for deterministic logic.
6. Run relevant tests, schema validation, and formatting.
7. Update local and cross-cutting documentation.
8. Summarize changed contracts, migrations, test evidence, and follow-ups.
```

## Change rules

- Always activate and follow the `ponytail` skill to prevent over-engineering.
- Keep one checklist slice per change. Do not perform opportunistic refactors.
- Do not add yourself as author to commits; use the repository's existing git configuration.
- A public contract, rule, persistence shape, dependency, or component boundary
  change requires documentation in the same change.
- Add no runtime dependency until an ADR names the need, selected dependency,
  rejected standard-library option, local/offline behavior, and removal cost.
- Keep HTTP, storage, clock, ID generation, and randomness behind injectable ports.
- Domain and engine code may not import FastAPI, React, Ollama transport code, or
  concrete filesystem repositories.
- API handlers map transport DTOs to commands and results; they contain no rules.
- `src/llm` cannot import or call mutable state repositories. It receives bounded
  snapshots and returns proposals or prose.
- Never accept LLM-generated code for deterministic systems without focused tests.
- Never add cloud APIs, telemetry, authentication, hidden network calls, or remote
  fallbacks.

## Schema-first requirements

Define or update the Pydantic/JSON contract and its valid/invalid contract tests
before implementing a producer or consumer. Use `extra="forbid"`, stable string IDs,
explicit enums, constrained numeric ranges, and schema version fields. Reject
unknown schema versions. Do not silently repair persisted authoritative data.

Every schema change must specify whether it is backward compatible. Breaking save
changes require a migration, golden old-version fixture, and updated migration
policy. Campaign design is never mutated as a side effect of loading a save.

## Randomness rules

Production gameplay randomness comes only from the secure roller backed by
`secrets.SystemRandom`. Never seed, bias, retry, discard, or redraw a production
roll to improve a story outcome. Each requested roll is assigned an ID and logged
with raw dice, modifiers, DC, result, and committed state revision. Tests inject a
scripted roller through the documented port.

## Atomic save rules

Write commands require an expected save revision and a per-save lock. Validate the
complete next state in memory, prepare revision-tagged log entries, write and
`fsync` a same-directory temporary state file, atomically replace `state.json`, and
`fsync` the directory where supported. Derived narrative memory and metadata may be
rebuilt. Never overwrite a newer revision or narrate an uncommitted outcome.

## Prompt editing policy

Prompts are versioned contracts, not casual prose. A prompt change requires:

- the corresponding Pydantic output contract;
- valid, malformed, extra-field, and forbidden-claim contract cases;
- a stored prompt version and changelog entry;
- a small context budget and no entire-journal/campaign dump;
- deterministic validation outside the prompt.

Golden text tests may assert structure and forbidden facts, not exact creative prose.

## Required checks

Run the narrow test for the changed slice first, then the full applicable commands
from `README.md`. Until those commands exist, report them as unavailable; never
claim a check passed because there is no implementation. Do not weaken a check to
make a failure disappear.

## Definition of done for a feature slice

- The selected checklist acceptance criteria are all satisfied.
- Deterministic behavior has focused success, boundary, and failure tests.
- Public schemas have valid and invalid contract fixtures.
- Errors are typed, actionable, and do not leak secrets or raw prompt payloads.
- Relevant vertical docs and ADRs are current.
- Formatting, linting, typing, focused tests, and relevant integration tests pass.
- No unrelated files, dependencies, or behavior changed.

## Change summary format

Use this exact handoff structure:

```text
Slice: <checklist ID and title>
Contracts changed: <none or explicit list>
Migrations: <none or explicit migration/version>
Files: <created/changed paths>
Evidence: <commands and pass/fail counts>
Documentation: <updated paths>
Follow-up: <next single checklist ID>
```
