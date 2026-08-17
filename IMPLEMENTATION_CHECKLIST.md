# Implementation Checklist

This is the execution script for a low-reasoning implementation model. The repository
is currently setup-only. Checked `SETUP-*` items are documentation/configuration work;
all unchecked items create or change implementation and must be done later.

## How to execute one slice

1. Pick the first unchecked item whose `Depends` items are checked.
2. Read root `CONTEXT.md`, root `AGENT.md`, then every file in the item's **Read** line.
3. State the listed invariant in the work log before editing.
4. Create/change only the listed files unless a test import requires `__init__.py`.
5. Write the named tests first, run them to see the expected failure, then implement.
6. Run the item's focused command and the existing full backend/frontend checks.
7. Update docs only if behavior differs from the already-written specification. A
   difference requires a named reason and usually an ADR; never improvise silently.
8. Check the box only after every **Accept** statement is true. End the turn. Do not
   start the next slice.

If a dependency/API version makes an exact instruction impossible, stop and report
the command/error plus the smallest documented alternative. Do not swap frameworks,
storage formats, model providers, formulas, or field names.

## Global coding choices (do not reconsider per slice)

- Backend: Python 3.12, Pydantic v2, FastAPI, HTTPX, Uvicorn; `uv` lock/install.
- Quality: Ruff formatting/lint, strict mypy, Pytest; no network in normal tests.
- Python packages are the top-level `app`, `domain`, `engine`, `campaign`, `llm`, and
  `api` packages under `src/`, installed editable by Hatch/uv.
- Frontend: React + strict TypeScript + Vite, Vitest, Testing Library, axe; npm lockfile.
- Models: a shared strict Pydantic base (`extra="forbid"`, enum values serialized),
  frozen for definitions/value objects and validated reconstruction for runtime state.
- Errors: typed code and safe structured details; never rule decisions as exception text.
- IDs/clock/random/filesystem/model calls are injected behind the documented ports.
- Integer/rational calculations use explicit helper functions; no gameplay floats.
- A state command returns a new validated state and typed events; it never mutates the
  loaded object after a later failure could leave a partial result.
- Only `state.json` is authoritative. Logs are audit records and narration is display.

---

## Milestone 0 — Finish executable project bootstrap

- [x] **SETUP-01 — Inspect empty workspace and establish scope**
  - Result: confirmed no existing files/Git repository and applied setup-only boundary.
- [x] **SETUP-02 — Create documentation and directory scaffold**
  - Result: created root, architecture, design, schema, prompt, UX, source, test, script,
    campaign, and workflow directories without runtime implementation.
- [x] **SETUP-03 — Record architecture and engineering contracts**
  - Result: canonical decisions, mechanics, field contracts, security, save transaction,
    prompt roles, UI behavior, and folder ownership are documented.
- [x] **SETUP-04 — Create low-reasoning implementation checklist**
  - Result: this file sequences implementation into bounded, testable slices.

- [x] **BOOT-01 — Create importable empty backend packages and lock Python dependencies**
  - Depends: SETUP-04
  - Read: `src/CONTEXT.md`, `src/AGENT.md`, ADR-008 and ADR-011.
  - Create: `src/{app,domain,engine,campaign,llm,api}/__init__.py`; `uv.lock`.
  - Change: `pyproject.toml` only to configure Hatch's six package paths and Pytest
    `pythonpath=["src"]`; remove `tool.uv.package=false` if still present.
  - Do: first verify `python3.12` (or newer) and `uv` are available. If `uv` is missing,
    stop and ask for approval to install that host-level prerequisite; do not invent a package
    workflow. Every `__init__.py` contains only a module docstring and
    `__all__: list[str] = []`. Run `uv lock`, then `uv sync --all-groups`; add no dependency.
  - Test: `uv run python -c "import api, app, campaign, domain, engine, llm"`.
  - Accept: import exits 0, lockfile is committed, no app/model/network/file I/O occurs.

- [x] **BOOT-02 — Add the backend test harness and import smoke test**
  - Depends: BOOT-01
  - Read: `tests/CONTEXT.md`, `tests/AGENT.md`.
  - Create: `tests/conftest.py`, `tests/unit/test_package_imports.py`.
  - Do: fixtures provide fixed UTC clock, sequential ID generator, and tmp campaign root;
    do not create game models yet. Test imports every package and asserts no logging/files.
  - Test: `uv run pytest tests/unit/test_package_imports.py -q`.
  - Accept: test passes, `uv run ruff check .` and `uv run mypy src tests` pass.

- [x] **BOOT-03 — Add documentation/scaffold validation script**
  - Depends: BOOT-02
  - Read: root `AGENT.md`, `scripts/CONTEXT.md`, documentation hierarchy in bootstrap.
  - Create: `scripts/check_scaffold.py`, `tests/unit/test_check_scaffold.py`.
  - Do: pure functions verify required root/docs/context/manual paths and Markdown links;
    CLI reports stable relative paths and exits 0/1. It must not require source code files
    scheduled later and must not scan `.git`, caches, campaigns saves, or node modules.
  - Test: `uv run pytest tests/unit/test_check_scaffold.py -q`; then
    `uv run python scripts/check_scaffold.py`.
  - Accept: valid repo passes; tmp copied scaffold missing one required file fails with
    that relative path; broken local link fails deterministically.

- [x] **ARCH-01 — Enforce backend import boundaries without a new dependency**
  - Depends: BOOT-02
  - Read: `docs/architecture/component-boundaries.md`, all `src/*/CONTEXT.md` files.
  - Create: `tests/unit/test_architecture_imports.py`.
  - Do: parse Python AST below `src/` and enforce: domain cannot import other project
    packages/FastAPI/HTTPX; engine cannot import app/api/campaign/llm/FastAPI; llm cannot
    import api/app or concrete state/campaign storage modules; api cannot import rule
    submodules. Keep a small documented allowlist for TYPE_CHECKING only if necessary.
  - Test: `uv run pytest tests/unit/test_architecture_imports.py -q`.
  - Accept: current tree passes and isolated sample violations for domain and engine fail.

- [x] **BOOT-04 — Add setup-only CI**
  - Depends: BOOT-03, ARCH-01
  - Read: `README.md`, ADR-011.
  - Create: `.github/workflows/test.yml`.
  - Do: on push/PR, checkout; install the Python version from `pyproject.toml`; install uv;
    run `uv sync --locked --all-groups`, scaffold check, Ruff format/check, strict mypy,
    and Pytest. Pin actions by immutable commit SHA with version comment. No secrets,
    Ollama, network tests, npm, campaign generation, or artifact upload yet.
  - Test: validate YAML locally if an existing parser is available; run every CI command.
  - Accept: all commands pass locally and workflow has least permissions (`contents: read`).

---

## Milestone 1A — Campaign schema contracts

- [x] **SCHEMA-01 — Implement strict common values and diagnostics**
  - Depends: BOOT-02
  - Read: `docs/schemas/CONTEXT.md`, `campaign-pack.md` common conventions.
  - Create: `src/domain/models/{__init__,common,diagnostics}.py` and
    `tests/unit/domain/test_common_models.py`.
  - Do: implement `StrictModel`, `FrozenModel`, `EntityId`, UTC datetime validator,
    `SemanticVersion`, `Rational`, and `Diagnostic`. Use annotated strings/types and
    stable diagnostic sort key; reject bool where an integer is required.
  - Test: valid boundaries plus bad IDs, whitespace-only text, naive timestamps, zero
    denominator, extra fields, non-finite/boolean numeric values.
  - Accept: focused tests and schema representation are deterministic; no I/O imports.

- [x] **SCHEMA-02 — Implement campaign meta and style-bible models**
  - Depends: SCHEMA-01
  - Read: `docs/schemas/campaign-pack.md` meta/style sections and worldbuilding doc.
  - Create: `src/domain/models/{campaign_meta,style_bible}.py`,
    `tests/unit/domain/test_campaign_meta_style.py`.
  - Do: implement exact enums/fields/ranges; `content_fingerprint` must be 64 lowercase
    hex when non-null; published meta requires it, draft meta forbids it.
  - Test: smallest/full valid and invalid status/fingerprint, sensory list, example count,
    duplicate banned phrase case-folding, art-style reference.
  - Accept: models reject unknown fields and serialize enums/UTC exactly as documented.

- [x] **SCHEMA-03 — Implement world and faction models**
  - Depends: SCHEMA-01
  - Read: campaign schema `world.json` section and worldbuilding design.
  - Create: `src/domain/models/world.py`, `tests/unit/domain/test_world_models.py`.
  - Do: implement power system, faction relationship, faction, major location, world,
    and file root. Local resident fields must not exist in world models.
  - Test: required non-empty power lists, stance bounds, self/duplicate faction edges,
    duplicate IDs, unknown fields, campaign ID validation.
  - Accept: local validation catches self/duplicate edges without loading other files.

- [x] **SCHEMA-04 — Implement area, resident, object, encounter, and secret models**
  - Depends: SCHEMA-01
  - Read: campaign schema `areas.json` section; freeform action design.
  - Create: `src/domain/models/area.py`, `tests/unit/domain/test_area_models.py`.
  - Do: exact models/enums/ranges; reject self/duplicate connections and duplicate local
    entity IDs; require a core clue to have at least one lead and reveal condition.
  - Test: smallest one-area root and each boundary/duplicate/empty core clue failure.
  - Accept: no cross-file existence checks are hidden in these local models.

- [x] **SCHEMA-05 — Implement character and companion campaign models**
  - Depends: SCHEMA-01
  - Read: campaign schema characters section; party and progression docs.
  - Create: `src/domain/models/character.py`, `tests/unit/domain/test_character_models.py`.
  - Do: `StatName`, exact-six `StatBlock`, background, major NPC, companion, relationship
    rule, and file root; starting loadout subset/unique/max-four invariant.
  - Test: missing/extra stat, out-of-range bonus/stat, loadout unknown/duplicate/fifth,
    companion usable-action bounds, duplicate character IDs.
  - Accept: models implement authored definitions only, not runtime relationship state.

- [x] **SCHEMA-06 — Implement skill, effect, tree, and fusion campaign models**
  - Depends: SCHEMA-01, SCHEMA-05
  - Read: campaign schema skills section; progression and combat docs.
  - Create: `src/domain/models/skill.py`, `tests/unit/domain/test_skill_models.py`.
  - Do: closed effect-kind/target enums; exact five skill levels ordered 1..5; exact
    default effect bands; structured prerequisites; tree nodes/edges; sorted two-source
    fusion recipe and point-buy definition.
  - Test: missing/duplicate level, bad mana, arbitrary effect kind, malformed effect
    table, tree self/unknown local edge, fusion source/result/backup conflicts, wrong
    point-buy table.
  - Accept: no formula strings/eval fields; all collections and bounds match docs.

- [x] **SCHEMA-07 — Implement item and enemy campaign models**
  - Depends: SCHEMA-01, SCHEMA-06
  - Read: campaign schema item/enemy sections; combat and progression docs.
  - Create: `src/domain/models/{item,enemy}.py`,
    `tests/unit/domain/test_item_enemy_models.py`.
  - Do: discriminated item mechanic union using known effect primitives; item rarity/type;
    loot, behavior, escape policy reference, and enemy archetype. Enforce unique stack=1
    and non-empty combat skills.
  - Test: numeric bounds, quest/unique stack, flavor max, bad arbitrary mechanics,
    reversed loot quantities, empty enemy action set, extra fields.
  - Accept: enemy power rating remains an asserted value to validate later, not computed.

- [x] **SCHEMA-08 — Implement plot, opportunity, clock, and balance campaign models**
  - Depends: SCHEMA-01
  - Read: campaign schema plot/balance sections; plot and difficulty docs.
  - Create: `src/domain/models/{plot,balance}.py`,
    `tests/unit/domain/test_plot_balance_models.py`.
  - Do: typed predicate/effect references (no executable strings); exact milestone,
    opportunity, clock, difficulty, XP, modifier/effect, encounter, fusion, and boss
    fields; require exact Story/Normal/Hard ratios/DC/luck values.
  - Test: duplicate/missing starts/endings locally, invalid clock, float ratio, unordered
    XP, missing profile, wrong difficulty constant, unknown predicate type.
  - Accept: graph reachability/cross-file checks remain for validation slices.

- [x] **SCHEMA-09 — Assemble CampaignPack and generate checked-in JSON Schemas**
  - Depends: SCHEMA-02, SCHEMA-03, SCHEMA-04, SCHEMA-05, SCHEMA-06, SCHEMA-07, SCHEMA-08
  - Read: all `docs/schemas/campaign-pack.md`; ADR-009.
  - Create: `src/domain/models/campaign_pack.py`, `scripts/generate_schemas.py`,
    `schemas/campaign/*.schema.json`, `tests/contract/test_campaign_json_schemas.py`.
  - Do: aggregate holds the nine typed roots; generator writes one deterministic Pydantic
    JSON Schema per root with sorted keys/newline. `--check` compares without writing.
  - Test: each smallest dict validates through Pydantic; generated snapshots are current;
    extra fields and wrong schema/campaign ID fail.
  - Accept: `uv run python scripts/generate_schemas.py --check` passes after generation;
    generated files are never hand-edited.

---

## Milestone 1B — Campaign validation and tiny fixture

- [x] **VALID-01 — Add individual file parse diagnostics and aggregate identity checks**
  - Depends: SCHEMA-09
  - Read: campaign schema cross-file validation; campaign folder rules.
  - Create: `src/engine/validation/{__init__,campaign_files}.py`,
    `tests/unit/engine/test_campaign_file_validation.py`.
  - Do: accept already-decoded filename->object mapping; collect Pydantic errors as stable
    diagnostics; require exact nine filenames and shared version/campaign ID.
  - Test: missing/extra filename, malformed root, mismatched campaign/version, multiple
    simultaneous errors sorted by file/pointer/code.
  - Accept: returns all diagnostics and no filesystem/model operations.

- [x] **VALID-02 — Build global typed ID index and validate references**
  - Depends: VALID-01
  - Read: every reference rule in campaign schema and component boundaries.
  - Create: `src/engine/validation/references.py`,
    `tests/unit/engine/test_campaign_references.py`.
  - Do: index IDs with entity type/source pointer; reject ambiguous global duplicates and
    resolve every documented reference against expected type. Output stable diagnostics.
  - Test: one valid minimal aggregate plus unknown faction/area/skill/item/milestone,
    wrong-type reference, and duplicate global ID cases.
  - Accept: validator never resolves by display name and reports source + target details.

- [x] **VALID-03 — Validate area, skill-tree, and milestone graphs**
  - Depends: VALID-02
  - Read: campaign schema graph rules and plot design.
  - Create: `src/engine/validation/graphs.py`,
    `tests/unit/engine/test_campaign_graphs.py`.
  - Do: pure deterministic graph functions for reciprocal area edges, skill-tree DAG,
    milestone reachability to endings, explicit bounded cycles, and opportunity parents.
  - Test: valid graphs, one-way area, tree cycle, unreachable milestone/ending, illegal
    milestone cycle, unknown parent (even if reference validator also catches it).
  - Accept: diagnostics identify every involved ID; traversal order is stable.

- [x] **VALID-04 — Validate balance, combat viability, and fusion safeguards**
  - Depends: VALID-02
  - Read: balance schema, difficulty/combat/progression/party docs.
  - Create: `src/engine/validation/balance.py`,
    `tests/unit/engine/test_campaign_balance.py`.
  - Do: implement the structured enemy power formula from `balance.json`; compare reported
    rating/encounter targets; enforce level effect/mana bounds, fusion power budget,
    catalyst type, enemy sustainable action, and companion backup/min-action invariant.
  - Test: one valid case and one focused failing case for every rule/rounding boundary.
  - Accept: integer/rational math only; model-provided rating never bypasses recomputation.

- [x] **FIXTURE-01 — Create the smallest valid campaign and targeted invalid fixtures**
  - Depends: VALID-03, VALID-04
  - Read: all campaign schema docs and Milestone 1 fixture requirement.
  - Create: `tests/fixtures/campaign_minimal_valid/design/*.json` (nine files), a fixture
    manifest, and invalid overlay files for unknown reference, graph, balance, point-buy,
    and extra-field failures; `tests/contract/test_campaign_fixtures.py`.
  - Do: fixture has one area, two resident NPCs (one companion may instead be major),
    exactly two objects, one enemy, one start/ending milestone (same allowed only if
    explicitly terminal), and one authored opportunity. Keep prose short and original.
  - Test: valid pack has zero diagnostics; each invalid overlay asserts exact one primary
    code and JSON pointer; test fixture counts explicitly.
  - Accept: valid and invalid failures are for intended reasons, no generated/model data.

- [x] **CAMP-01 — Implement safe campaign directory loading**
  - Depends: FIXTURE-01
  - Read: campaign storage context, threat model, campaign/save ADR.
  - Create: `src/campaign/storage/{__init__,paths,json_io,repository}.py`,
    `tests/integration/campaign/test_campaign_repository.py`.
  - Do: resolve campaign ID under injected root; reject traversal/absolute/symlink escape;
    enforce file/count/byte/depth/duplicate-key limits; parse nine files; run full
    validators; return typed pack or diagnostics without partial pack.
  - Test: valid load, each invalid fixture, traversal, absolute, symlink where supported,
    duplicate JSON key, oversized file, missing file, unknown newer version.
  - Accept: no path from JSON/model controls disk; errors never expose unnecessary absolute
    paths; normal load makes no network calls.

- [x] **CAMP-02 — Implement canonical JSON and campaign fingerprint verification**
  - Depends: CAMP-01
  - Read: campaign schema meta fingerprint; ADR-003.
  - Create/change: `src/campaign/storage/canonical.py`, repository, and
    `tests/unit/campaign/test_campaign_fingerprint.py`.
  - Do: canonical UTF-8/sorted/no-whitespace serialization; fixed design filename order;
    omit meta fingerprint value during digest; calculate SHA-256; published load requires
    exact fingerprint while draft load exposes computed preview only.
  - Test: key/formatting order stability, content change difference, fingerprint omission,
    published mismatch, repeated calculation.
  - Accept: digest is platform-independent and contains no timestamps/paths.

- [x] **SCRIPT-01 — Implement campaign validation CLI**
  - Depends: CAMP-02
  - Read: scripts context/manual and campaign diagnostic contract.
  - Create: `scripts/validate_campaign.py`, `tests/integration/scripts/test_validate_campaign.py`.
  - Do: accept one explicit campaign directory or ID+root, `--json`, and `--check-fingerprint`;
    call repository/validators; stable human/JSON diagnostics; exit 0 valid, 1 invalid,
    2 usage/environment. No model call or repair.
  - Test: help, valid fixture, invalid fixture, unsafe path, JSON output, exit codes.
  - Accept: README validation command becomes genuinely runnable and is updated if needed.

---

## Milestone 1C — Point buy and runtime-state contracts

- [x] **CHAR-01 — Implement and test exact 27-point-buy validation**
  - Depends: SCHEMA-05, SCHEMA-06
  - Read: progression point-buy section and campaign PointBuyDefinition.
  - Create: `src/domain/rules/{__init__,point_buy}.py`,
    `tests/unit/domain/test_point_buy.py`.
  - Do: pure `validate_point_buy(stats, definition)` returns typed success with total or
    errors for missing/extra stat, below/above pre-bonus range, unavailable cost, total
    not exactly 27. Separate `apply_background_bonus` validates target/max 17.
  - Test: canonical valid allocation, 26/28, all boundary scores, malformed stat set,
    +1/+2 valid, post-bonus 18 rejection; assert input unchanged.
  - Accept: no auto-spend, clamping, random stats, or campaign/world dependency.

- [x] **STATE-01 — Implement player inventory, skill, and resource runtime models**
  - Depends: SCHEMA-06, SCHEMA-07, CHAR-01
  - Read: runtime-state Player section; progression and difficulty docs.
  - Create: `src/domain/models/{runtime_common,player_state}.py`,
    `tests/unit/domain/test_player_state.py`.
  - Do: resource values/maxima, status instance, inventory/equipment, known skill, fusion
    history, player state and invariants. Enforce six stats, resource bounds, positive
    inventory, equipment ownership, known/unique max-four loadout, luck bounds.
  - Test: smallest valid and every invariant/boundary/extra-field failure.
  - Accept: campaign reference existence remains a cross-state validator, not guessed here.

- [x] **STATE-02 — Implement companion, party, location, NPC/object override models**
  - Depends: STATE-01
  - Read: runtime-state party/location sections; party design.
  - Create: `src/domain/models/{party_state,world_state}.py`,
    `tests/unit/domain/test_party_world_state.py`.
  - Do: exact runtime fields; protagonist + max-three unique active companions; active IDs
    present in companion map; typed life/availability/object states; discovered areas.
  - Test: missing/duplicate/fourth companion, protagonist duplication, invalid resources,
    contradictory dead+active/unavailable state, unknown extra override value.
  - Accept: no authored definition data is copied except required runtime snapshot values.

- [x] **STATE-03 — Implement plot, pending-check, and combat snapshot models**
  - Depends: STATE-01
  - Read: runtime-state plot/pending/combat sections; action/combat/plot docs.
  - Create: `src/domain/models/{plot_state,check_state,combat_state}.py`,
    `tests/unit/domain/test_plot_check_combat_state.py`.
  - Do: opportunity/milestone/clock states, named modifiers and five allowed check outcomes,
    combat participant/status/order/phase/tie-break/policies. Keep calculations out.
  - Test: state enum/range, check DC arithmetic consistency, duplicate targets/order,
    current index, resource bounds, terminal stored-phase rejection.
  - Accept: pending check has no roll; normal persisted combat phase is active only.

- [x] **STATE-04 — Implement root state, command receipt, journal, roll, memory, and meta**
  - Depends: STATE-02, STATE-03
  - Read: all runtime-state docs and save design.
  - Create: `src/domain/models/{runtime_state,audit,narrative_memory,save_meta}.py`,
    `tests/unit/domain/test_runtime_roots.py`.
  - Do: exact roots/row fields and invariants; typed effect union from domain events;
    bound receipts 100 and narrative memory 32 KiB through serialization check helper.
  - Test: smallest full state, resource/mode inconsistencies, bad revision/log values,
    raw roll range/selected index/total, memory event count/size, extra fields.
  - Accept: timestamps are audit-only UTC; state contains no narrator prose/absolute paths.

- [x] **STATE-05 — Generate runtime JSON Schemas and valid/invalid state fixtures**
  - Depends: STATE-04, SCHEMA-09
  - Read: runtime-state and migration policy.
  - Change: `scripts/generate_schemas.py`.
  - Create: `schemas/runtime/*.schema.json`, `tests/fixtures/save_minimal_valid/*`, focused
    invalid state/log files, `tests/contract/test_runtime_json_schemas.py`.
  - Do: generate schemas for five files/rows; fixture binds to minimal campaign computed
    fingerprint; revision 0, no combat/pending check. Invalid cases assert intended code.
  - Test: generator `--check`, Pydantic round-trip, JSON lines individually validate.
  - Accept: serialization -> validation -> serialization is semantically identical.

---

## Milestone 1D — Dice, saves, and deterministic action slice

- [x] **DICE-01 — Define random port, secure d20 source, and scripted test source**
  - Depends: STATE-04
  - Read: ADR-005; difficulty RNG section; engine context/manual.
  - Create: `src/engine/dice/{__init__,ports,secure,testing}.py`,
    `tests/unit/engine/test_random_sources.py`.
  - Do: `RandomSource.roll(sides)` protocol; production `SecureRandomSource` owns one
    `secrets.SystemRandom` and uses inclusive 1..sides; reject sides <2 before drawing.
    `ScriptedRandomSource` is importable only from a testing module and consumes exact
    queued values while checking range/call count.
  - Test: patch the SystemRandom instance to assert one inclusive call; scripted order,
    exhaustion, bad queued value, bad sides; architecture import rules still pass.
  - Accept: production exposes no seed/state/retry API and does not import `random.Random`.

- [x] **DICE-02 — Implement roll arithmetic and audit-record construction**
  - Depends: DICE-01
  - Read: runtime `RollRecord`; difficulty outcome precedence; combat effect bands.
  - Create: `src/engine/dice/{checks,effects,service}.py`,
    `tests/unit/engine/test_dice_service.py`.
  - Do: pure named-modifier sum; exploration band precedence; combat band mapping; service
    accepts injected RNG/clock/ID and produces result + complete uncommitted RollRecord
    tagged with supplied transaction/revision/command. No persistence in service.
  - Test: raw 1/20 precedence, exact DC, DC-1/-3/-4, negative modifiers, no-DC tie-break,
    every effect band, exactly one source call, audit arithmetic and metadata.
  - Accept: displayed/audited values derive from the same result object; no hidden draws.

- [x] **SAVE-01 — Implement strict save serialization and read-only loading**
  - Depends: STATE-05, CAMP-02
  - Read: save design, transaction/recovery flow, threat model.
  - Create: `src/engine/state/{__init__,ports,errors}.py`,
    `src/campaign/storage/save_reader.py`,
    `tests/integration/state/test_save_reader.py`.
  - Do: `SaveRepository` protocol types; safe save/campaign ID path resolution; byte/depth/
    duplicate-key limits; parse state + each JSONL row + derived roots; verify campaign
    identity/fingerprint and state/log invariants. Prepared rows above state revision are
    reported separately, not applied.
  - Test: minimal fixture round-trip, unsafe paths/symlink, corrupt/truncated JSON/JSONL,
    wrong fingerprint/version, committed row above revision, missing derived file status.
  - Accept: load is read-only, preserves corrupt input, and never silently defaults fields.

- [x] **SAVE-02 — Implement transition, expected revision, and command idempotency**
  - Depends: SAVE-01
  - Read: system overview command/event model; save command receipt rules.
  - Create: `src/engine/state/{commands,transition,idempotency}.py`,
    `tests/unit/engine/test_state_transition.py`.
  - Do: immutable command envelope, canonical request hash excluding transport noise,
    candidate transition model, receipt lookup; reject stale revision; identical duplicate
    returns prior safe result/roll IDs; mismatched duplicate conflicts.
  - Test: happy transition, state revision exactly +1, stale, identical duplicate, ID reuse
    with different payload, receipt bound/eviction, no input mutation.
  - Accept: duplicate path calls no handler/RNG and creates no new event.

- [x] **SAVE-03 — Implement atomic state commit and prepared JSONL records**
  - Depends: SAVE-02
  - Read: ADR-010 and exact save transaction flow.
  - Create: `src/campaign/storage/save_repository.py`,
    `tests/integration/state/test_atomic_save_commit.py`.
  - Do: per-save in-process lock; re-read revision under lock; validate transition; append
    prepared journal/roll rows and fsync; same-directory unique temp state, fsync, re-read,
    validate, `os.replace`, best-effort directory fsync; atomically refresh derived roots;
    cleanup own temp only. One process/worker is the documented v1 boundary.
  - Test: commit/round-trip, concurrent stale writer, duplicate command, injected failure
    before/after each ordered write/replace, temp cleanup, prepared rows remain uncommitted,
    narration callback is not part of repository.
  - Accept: old or complete new state is readable after every injected failure; never partial.

- [x] **SAVE-04 — Add autosave recovery snapshots and recovery inspection**
  - Depends: SAVE-03
  - Read: save slots/recovery section and threat model.
  - Create: `src/campaign/storage/recovery.py`,
    `tests/integration/state/test_save_recovery.py`.
  - Do: retain three post-commit state/meta snapshots with revision; validate before use;
    identify stale derived files and prepared-above-state rows; rebuild derived metadata;
    restore only to a new staging copy then replace after explicit function argument.
  - Test: snapshot rotation 1..5, corrupt latest, valid older selection, no-snapshot, derived
    rebuild, orphan report, injected recovery failure preserves original.
  - Accept: no automatic destructive restore and at least one valid source remains.

- [x] **SAVE-05 — Implement v1 migration runner with no-op/current guards**
  - Depends: SAVE-04
  - Read: migration policy and scripts rules.
  - Create: `src/engine/state/migrations/{__init__,registry,runner}.py`,
    `scripts/migrate_save.py`, `tests/unit/engine/test_migration_runner.py`,
    `tests/integration/scripts/test_migrate_save.py`.
  - Do: registry supports sequential pure steps but v1 has none; current version validates
    and copies only with explicit `--copy-to`; newer/zero rejected; CLI dry-run default,
    explicit destination, backup/report rules. Do not pretend a no-op is a migration.
  - Test: current dry run, invalid/newer, missing step using synthetic in-test registry,
    source unchanged, help/exit codes, injected failure.
  - Accept: architecture is ready for v2 without manufacturing an unnecessary v0 format.

- [x] **LLMCON-01 — Implement strict action-proposal contract and JSON parser**
  - Depends: SCHEMA-01
  - Read: `docs/schemas/llm-contracts.md` ActionProposal and prompt action spec.
  - Create: `src/llm/contracts/{__init__,common,action}.py`,
    `src/llm/orchestration/json_parser.py`,
    `tests/contract/test_action_proposal_contract.py`.
  - Do: exact V1 fields/invariants; duplicate-key-detecting parser accepts one object only,
    enforces input/output bytes, matching versions/request ID, no Markdown/prose/NaN.
  - Test: complete matrix listed in LLM contracts including fabricated ordinal and explicit
    prohibited mutation/DC/die/ID fields as extra-field failures.
  - Accept: parser performs no repair or semantic entity resolution and returns typed error.

- [x] **ACTION-01 — Build bounded candidate sets and deterministic entity resolver**
  - Depends: CAMP-01, STATE-04, LLMCON-01
  - Read: freeform validation order and action contract entity mentions.
  - Create: `src/engine/actions/{__init__,candidates,resolver}.py`,
    `tests/unit/engine/test_entity_resolver.py`.
  - Do: select visible/present/reachable area entities, active party, owned inventory, and
    known facts into stable ordinals; resolve valid ordinal + compatible mention text/type;
    return ambiguity/unresolved diagnostics; never fuzzy-pick an equal candidate.
  - Test: known local object/NPC/item, hidden/dead/unavailable/remote exclusion, two same-name
    ambiguity, wrong ordinal/type/text, stable ordering, malicious arbitrary ID text.
  - Accept: model never gets or returns mutable objects; selected facts fit configured caps.

- [x] **ACTION-02 — Validate standard exploration operations against state**
  - Depends: ACTION-01
  - Read: freeform actions; component rule ownership; plot protections.
  - Create: `src/engine/actions/{operations,validator}.py`,
    `tests/unit/engine/test_action_validator.py`.
  - Do: closed operation dispatch; validate combat inactive, existence, location/reachability,
    ownership/quantity, life/availability, known capabilities, world law, and plot/outcome
    allowlist. Return `ValidatedAction`, `PartialAction`, or typed rejection—no effect yet.
  - Test: valid talk/inspect/use/travel, absent inventory, remote/dead NPC, locked connection,
    unknown operation, active combat, protected fact, interpreter-valid downgraded to invalid.
  - Accept: all rejections leave state unchanged and consume no RNG.

- [x] **ACTION-03 — Validate creative capability/object combinations**
  - Depends: ACTION-02
  - Read: creative-action section; item/object schema capability fields.
  - Create: `src/engine/actions/creative.py`,
    `tests/unit/engine/test_creative_actions.py`.
  - Do: match actor/item/environment capability tags against object predicates and its
    authored allowed effect IDs; select only exact authored route; produce applicable
    named modifiers from definition stacking keys. No generic creativity bonus.
  - Test: crowbar+crate valid fixture case, two-entity combination, missing capability,
    wrong object state, disallowed effect, duplicate stacking key highest-absolute rule,
    no invented object/content.
  - Accept: this satisfies entity-bound creative-action bootstrap requirement with tests.

- [x] **ACTION-04 — Decide check necessity and create/cancel pending checks**
  - Depends: ACTION-03, SAVE-02
  - Read: difficulty check necessity; freeform pending checks; PendingCheck schema.
  - Create: `src/engine/actions/check_builder.py`,
    `tests/unit/engine/test_pending_check.py`.
  - Do: map semantic label to base DC, apply difficulty adjustment once, compute named
    formula inputs, and require pre-authored five-band outcomes/stakes. Trivial resolves
    directly, impossible rejects, meaningful uncertainty creates one pending check.
    Implement cancel as revisioned transition without RNG.
  - Test: trivial/consequence-free/impossible/uncertain, each DC label/profile, one-pending
    guard, exact formula display, cancel, missing fail-forward outcome/core-clue route.
  - Accept: no die exists before explicit resolve command and DC is engine-owned.

- [x] **ACTION-05 — Resolve pending checks, effects, and luck atomically**
  - Depends: ACTION-04, DICE-02
  - Read: difficulty outcome/luck rules; runtime pending/roll/event schemas.
  - Create: `src/engine/actions/check_resolver.py`,
    `tests/unit/engine/test_check_resolver.py`.
  - Do: revalidate pending preconditions; draw one d20; choose documented band; construct only
    prevalidated typed effects; implement +2, reroll-accept-new, natural-1 downgrade with
    resource decrement and linked roll records; clear pending in candidate transition.
  - Test: all bands, impossible natural 20 impossible by precheck, all luck options/capacity,
    two recorded reroll values, stale precondition, duplicate command no extra draw, effect
    application failure leaves original state/pending unchanged.
  - Accept: state/event/roll effects agree exactly and core clue routes remain.

- [x] **ACTION-06 — Add deterministic submit/resolve exploration use cases**
  - Depends: ACTION-05, SAVE-03
  - Read: exploration data flow; system command model.
  - Create: `src/engine/actions/use_cases.py`,
    `tests/integration/actions/test_exploration_pipeline.py`.
  - Do: use case accepts an already-parsed proposal (no Ollama yet), loads campaign/save,
    runs candidates/resolution/validation, commits rejection only when audit design calls for
    it (otherwise no mutation), commits direct/pending/resolved actions, returns safe result.
  - Test: minimal fixture direct inspect, creative crowbar check, cancel, resolve success/
    partial/failure, stale revision, duplicate resolve; reload state/logs after each.
  - Accept: full deterministic vertical action flow works without FastAPI or Ollama.

- [x] **SCRIPT-02 — Add deterministic vertical-slice smoke command**
  - Depends: ACTION-06, CHAR-01
  - Read: scripts rules and Milestone 1 deliverables.
  - Create: `scripts/run_smoke_test.py`, `tests/integration/scripts/test_smoke_script.py`.
  - Do: in a temporary directory copy minimal campaign, create character/save with valid
    point buy, submit a fixed valid proposal, use scripted roll through dependency injection,
    commit/reload, validate event/roll. Print terse step results; never modify repo fixture.
  - Test: subprocess success output/exit 0 and injected invalid fixture/roll failure exit 1.
  - Accept: README smoke command is runnable; full backend checks pass without Ollama/network.

---

## Milestone 1E — Minimal local API (still no Ollama)

- [x] **API-01 — Implement settings, error envelopes, and application factory**
  - Depends: BOOT-01, SAVE-03
  - Read: app/api contexts, component HTTP mapping, threat model.
  - Create: `src/app/{config,dependencies,main}.py`, `src/api/schemas/common.py`,
    `src/api/routes/health.py`, `tests/unit/app/test_config.py`,
    `tests/integration/api/test_app_factory.py`.
  - Do: validated `STORYMODE_` settings; loopback host/Ollama URL; injected dependency
    container; `create_app()` and lifespan; safe error envelope/correlation ID; `/health`
    reports core/storage and `not_configured` model capabilities without calling network.
  - Test: import side-effect free, settings defaults/env overrides/rejections, app construct,
    health response/OpenAPI, safe 404/validation errors, exact CORS defaults.
  - Accept: factory tests use temp root; app never creates/downloads content on import.

- [x] **API-02 — Add campaign validation and character/save creation endpoints**
  - Depends: API-01, CAMP-02, CHAR-01, STATE-05
  - Read: API boundary, builder review (validation), screen map.
  - Create: `src/api/schemas/{campaigns,saves}.py`,
    `src/api/routes/{campaigns,saves}.py`,
    `tests/integration/api/test_campaign_save_routes.py`.
  - Do: GET campaign list/detail/validation; POST save with campaign ID/fingerprint, slot,
    name, background, exact stats, difficulty, command ID. Use a dedicated creation use case
    and atomic repository; do not put construction rules in route.
  - Test: valid create/reload, point-buy/background invalid 422, unknown campaign 404,
    duplicate command idempotency, unsafe IDs, response excludes hidden/path data.
  - Accept: OpenAPI uses typed DTOs and mutation response includes revision.

- [x] **API-03 — Add deterministic exploration endpoints using supplied test proposals**
  - Depends: API-02, ACTION-06
  - Read: exploration UX and action pipeline.
  - Create: `src/api/schemas/actions.py`, `src/api/routes/actions.py`,
    `tests/integration/api/test_action_routes.py`.
  - Do: production submit route must return 503 `interpreter_not_configured` until LLM slice;
    expose no endpoint that trusts client proposals. Resolve/cancel pending check routes call
    deterministic use cases. In tests, dependency override supplies fake interpreter port.
  - Test: fake valid/creative/invalid proposal flows, 503 without interpreter, visible check,
    resolve/cancel, stale 409, rule rejection 422, duplicate request no extra fake roll.
  - Accept: clients cannot inject ActionProposal/roll/DC/effects through HTTP.

- [x] **API-04 — Update smoke flow to exercise FastAPI in process**
  - Depends: API-03, SCRIPT-02
  - Read: README planned commands and API rules.
  - Change: `scripts/run_smoke_test.py`, smoke tests, README only if command differs.
  - Do: construct app with temp repositories, fake interpreter, scripted RNG; create save,
    submit action, resolve, reload through ASGI transport. Keep direct engine smoke helper too.
  - Test: `uv run python scripts/run_smoke_test.py`; full Pytest/Ruff/mypy/schema/scaffold.
  - Accept: Milestone 1 is runnable and tested with no real server, network, or Ollama.

---

## Milestone 2 — Deterministic combat vertical slice

- [x] **COMBAT-01 — Implement integer rational scaling and resource damage helpers**
  - Depends: STATE-03
  - Read: combat damage/rounding and difficulty profile math.
  - Create: `src/domain/rules/{arithmetic,combat_resources,difficulty}.py`,
    `tests/unit/domain/test_combat_arithmetic.py`.
  - Do: ties-up non-negative rational rounding, apply profile HP/damage once, armour-first
    damage result, resource clamp only during an intentional effect. Helpers return before/
    after/absorbed values and reject invalid persisted inputs instead of repairing them.
  - Test: zero/one, every `.5` edge, 7/10, 5/4, 1/2, 3/2, minimum positive HP,
    armour-only/exact/spill/no-armour/overkill; booleans/negative denominator rejected.
  - Accept: no gameplay float operations and no attack/armour-class calculation.

- [x] **COMBAT-02 — Start encounters and calculate deterministic turn order**
  - Depends: COMBAT-01, DICE-02
  - Read: combat encounter start/order; party size rules.
  - Create: `src/engine/combat/{__init__,encounter,turn_order}.py`,
    `tests/unit/engine/test_combat_start_order.py`.
  - Do: validate no active combat, known/present living participants, max party, encounter
    definitions; snapshot profile-scaled enemy values; order Speed then Dexterity; draw one
    d20 per still-tied participant, stable ID fallback; record every draw; create transition.
  - Test: one hero/enemy, speed order, Dexterity tie, RNG tie/collision fallback, dead/remote/
    duplicate participant, hard/story scaling, duplicate command no tie redraw.
  - Accept: no general initiative roll; order and audit reproduce from recorded values.

- [x] **COMBAT-03 — Implement turn-start mana and status processing**
  - Depends: COMBAT-02
  - Read: combat turn-start and status order.
  - Create: `src/engine/combat/{statuses,turns}.py`,
    `tests/unit/engine/test_combat_turns.py`.
  - Do: expire, process typed start-turn effects by `(priority,status_id)`, regenerate mana,
    skip newly defeated/unable actors, compute next living index/round. Use closed status
    handler registry; unknown persisted status is validation failure.
  - Test: cap regen, expiry boundary, ordering, damage-over-time defeat/skip, whole round,
    only-one-side remains, unknown status, original state unchanged on rejection.
  - Accept: no wall clock and no model narration in turn processing.

- [x] **COMBAT-04 — Validate skill commands and apply guaranteed base effects**
  - Depends: COMBAT-03
  - Read: combat allowed commands/skill resolution; skill schema.
  - Create: `src/engine/combat/{commands,skills,effects}.py`,
    `tests/unit/engine/test_combat_base_skills.py`.
  - Do: validate current actor, equipped/known skill level, mana, status, target rule,
    living target, explicit typed immunity; deduct mana then apply ordered base effects via
    closed registry, damage armour-first; create typed effect events. No effect die yet.
  - Test: valid damage/support, insufficient mana, wrong turn/target, unequipped skill,
    prevented status, known immunity, multi-target stable order, armour spill, rollback when
    a later base effect validation fails.
  - Accept: every valid base effect connects; there is no attack roll or generic miss.

- [x] **COMBAT-05 — Add one optional effect die and bonus-effect tables**
  - Depends: COMBAT-04
  - Read: combat effect-die rules; RollRecord.
  - Change: `src/engine/combat/skills.py` and tests; create
    `tests/unit/engine/test_combat_effect_die.py`.
  - Do: after successful base effects, draw exactly one d20 only if skill has a table and
    relevant target remains; map exact band; apply only defined bonus; natural 1 cannot
    revoke base; no die when base ended encounter/no relevant target.
  - Test: all five bands, no table, target defeated by base, bonus status/immunity,
    drawback bounded, duplicate command via use case fake no second draw.
  - Accept: result and audit clearly separate guaranteed base from bonus.

- [x] **COMBAT-06 — Implement Defend and Guarded**
  - Depends: COMBAT-04
  - Read: combat Defend exact 25% rule.
  - Create: `src/engine/combat/defend.py`,
    `tests/unit/engine/test_combat_defend.py`.
  - Do: 0-cost Defend applies non-stacking Guarded to next turn start; incoming positive
    damage consumes it and reduces 25%, reduction floor/min 1, before armour routing.
    Re-defend refreshes duration but does not stack magnitude.
  - Test: damage 1/3/4/5, armour routing, no-damage does not consume, expiry, refresh,
    actor prevented from acting, turn advances.
  - Accept: Guarded result is visible in event/status DTO and normal mana regen unchanged.

- [x] **COMBAT-07 — Implement authored flee and yield transitions**
  - Depends: COMBAT-03, DICE-02
  - Read: combat flee/yield and difficulty outcome rules.
  - Create: `src/engine/combat/{escape,consequences}.py`,
    `tests/unit/engine/test_combat_escape_yield.py`.
  - Do: engine advertises availability from encounter policy/state; flee consumes turn and
    uses one configured check with five authored effects; yield has no roll and applies
    exact authored consequence; successful terminal state reduces to encounter history.
  - Test: unavailable, all flee bands/profile DC, success enemy alive/world flag, failure
    advantage and next actor, yield allowed/denied, no yield draw, protected-route guard.
  - Accept: no generic always-flee/yield and no model-selected consequence.

- [x] **COMBAT-08 — Resolve victory, XP/loot, and protagonist soft defeat exactly once**
  - Depends: COMBAT-05, COMBAT-07
  - Read: combat defeat/victory, party defeat, progression discovery.
  - Create: `src/engine/combat/resolution.py`,
    `tests/unit/engine/test_combat_resolution.py`.
  - Do: detect side defeat after effects; apply authored XP/loot/flags; create history;
    protagonist defeat selects only encounter-authored valid soft consequence; true game-over
    requires endgame+telegraphed flags; companion zero HP follows authored non-death default.
  - Test: normal victory, loot quantity bounds via injected RNG only if table requires it
    (each audited), no duplicate grants, capture/injury/separation, invalid death/game-over,
    protected reachability, terminal combat removed from state.
  - Accept: narrator never supplies rewards/consequence and command replay is idempotent.

- [x] **COMBAT-09 — Add combat command use case and persistence integration**
  - Depends: COMBAT-06, COMBAT-08, SAVE-03
  - Read: combat data flow and engine command rules.
  - Create: `src/engine/combat/use_cases.py`,
    `tests/integration/combat/test_combat_pipeline.py`.
  - Do: start/allowed-actions/use-skill/defend/flee/yield commands; load campaign/save,
    validate expected revision/idempotency, invoke rules, commit state/events/rolls, return
    next allowed commands. One transition per command.
  - Test: full hero-vs-enemy fixture through victory, hard/story cases, defend, flee, soft
    defeat, stale/duplicate commands, reload after every turn, action parser guard active.
  - Accept: state remains valid after each persisted turn and all logs match transitions.

- [x] **API-05 — Expose typed combat endpoints and allowed actions**
  - Depends: COMBAT-09, API-03
  - Read: combat UX and API boundary.
  - Create: `src/api/schemas/combat.py`, `src/api/routes/combat.py`,
    `tests/integration/api/test_combat_routes.py`.
  - Do: endpoints start eligible authored encounter, get combat view, submit skill/defend/
    flee/yield; request carries command/revision and IDs only; map typed errors; response
    includes authoritative resources/order/log result/allowed commands.
  - Test: all commands, invalid injected damage/DC rejected by DTO extra-field rule, mode
    conflict, stale/duplicate, no narration dependency, OpenAPI snapshot update.
  - Accept: Milestone 2 full checks and smoke include one complete combat.

---

## Milestone 3 — Party, progression, plot, and clocks

- [x] **PARTY-01 — Implement recruit, activate, deactivate, leave, and availability rules**
  - Depends: STATE-02, SAVE-02
  - Read: party membership/availability and plot protections.
  - Create: `src/engine/progression/{__init__,party}.py`,
    `tests/unit/engine/test_party_membership.py`.
  - Do: authored-condition evaluator handles known predicate union; validate alive, recruited,
    co-located, available, non-hostile, not combat; max three; transitions/events exact.
  - Test: recruit/activate/deactivate, fourth, duplicate, remote/dead/captured/hostile, combat,
    authored leave condition, protected-route invalid departure, no input mutation.
  - Accept: narration/relationship prose cannot change membership.

- [x] **PARTY-02 — Validate companion authored builds and player-controlled combat actions**
  - Depends: PARTY-01, COMBAT-09
  - Read: party authored builds and combat actor rules.
  - Create: `src/engine/progression/companion_builds.py`,
    `tests/unit/engine/test_companion_builds.py`.
  - Do: construct runtime companion only from definition; enforce skill tree/loadout/minimum;
    combat allowed-actions works for current companion exactly like player with authored kit.
  - Test: valid construction/action, arbitrary protagonist skill rejected, invalid definition
    diagnostic, companion mana/status/target, no automatic AI action.
  - Accept: no respec or model-selected companion action path exists.

- [x] **PROG-01 — Implement XP thresholds and level-token grants**
  - Depends: STATE-01, VALID-04
  - Read: progression character levels and balance XP.
  - Create: `src/engine/progression/leveling.py`,
    `tests/unit/engine/test_leveling.py`.
  - Do: add non-negative authored XP, compute every crossed strictly increasing threshold,
    grant one token each, cap at table maximum, journal before/after. Reject negative XP.
  - Test: below/exact/multiple thresholds, cap, repeated grant idempotency at command layer,
    invalid table (defense), input unchanged.
  - Accept: levels are engine-derived from XP and tokens never silently spent.

- [x] **PROG-02 — Implement skill discovery, upgrade, and four-slot loadout changes**
  - Depends: PROG-01
  - Read: progression discovery/loadout/upgrades.
  - Create: `src/engine/progression/skills.py`,
    `tests/unit/engine/test_skill_progression.py`.
  - Do: validate authored acquisition source/conditions; grant level 1; one-token one-level
    upgrade through 5 with prerequisites; equip/unequip only outside combat, unique max four.
  - Test: each acquisition source category through parameterized definition, unknown/unmet,
    duplicate grant, levels/token/prerequisite/cap, fifth/duplicate/unknown loadout, combat.
  - Accept: all changes atomic and journal exact source/skill/before/after.

- [x] **PROG-03 — Implement player fusion transaction**
  - Depends: PROG-02
  - Read: exact seven fusion prerequisites and atomic result.
  - Create: `src/engine/progression/fusion.py`,
    `tests/unit/engine/test_player_fusion.py`.
  - Do: validate same owner/two level-5/recipe/unlocks/location-or-specialist/catalyst/no
    combat; consume source skills/catalyst, clean loadout, grant result, equip if any source
    equipped, free slot; construct complete event in one new state.
  - Test: success with both/one/neither equipped, every missing prerequisite separately,
    catalyst quantity, unordered source recipe, result already known, rollback on failure.
  - Accept: no partial consumption and no runtime-generated recipe/effect.

- [x] **PROG-04 — Implement companion fusion backup safeguard**
  - Depends: PROG-03, PARTY-02
  - Read: companion fusion safeguard and schema recipe fields.
  - Change: fusion module; create `tests/unit/engine/test_companion_fusion.py`.
  - Do: companion uses authored recipe/scope; grant immediate backup or record exact authored
    pending unlock; validate resulting usable action count and fixed tree; atomic rollback.
  - Test: immediate/pending backup, missing backup definition, minimum violation, source/
    catalyst rules, loadout after fusion, arbitrary player recipe rejected.
  - Accept: companion cannot become mechanically under-equipped.

- [x] **PLOT-01 — Implement milestone preconditions and protected transitions**
  - Depends: VALID-03, STATE-03
  - Read: campaign spine and runtime milestone state rules.
  - Create: `src/engine/plot/{__init__,predicates,milestones}.py`,
    `tests/unit/engine/test_milestones.py`.
  - Do: closed predicate evaluator over known state; lock/available/active/resolved transitions;
    apply only required authored outcomes; activate valid next nodes; preserve reachability;
    reject canonical/forbidden change effect.
  - Test: each state transition, unmet/then met, two next routes, ending, invalid skip/repeat,
    protected truth/reachability failure, stable event order.
  - Accept: model text is never an input to state transition effects.

- [x] **PLOT-02 — Implement opportunity frontier state transitions**
  - Depends: PLOT-01
  - Read: full opportunity graph rules.
  - Create: `src/engine/plot/opportunities.py`,
    `tests/unit/engine/test_opportunities.py`.
  - Do: add validated authored/runtime instance; active/deferred/locked/invalidated/resolved;
    defer rather than delete unchosen; invalidate only named predicate; successor references;
    maintain target 3–7 with explicit ending/no-valid diagnostics.
  - Test: every transition, duplicate parent/entity/outcome guards, 2/3/7/8 frontier,
    non-selection defer, meaningful invalidation, transformation/audit, protected fact.
  - Accept: opportunity history persists and no hidden pruning occurs.

- [x] **PLOT-03 — Validate runtime opportunity proposals independent of LLM transport**
  - Depends: PLOT-02
  - Read: OpportunityProposalV1 and opportunity runtime validation.
  - Create: `src/engine/plot/proposal_validator.py`,
    `tests/unit/engine/test_opportunity_proposals.py`.
  - Do: accept typed proposal/candidate set; resolve ordinals; validate parent reachability,
    existing entities, allowed outcomes/predicates/expiry, protected truth empty, balance/
    pacing, novelty; assign ID only after validation through injected generator.
  - Test: valid, unknown ordinal/parent, new canonical claim, duplicate active hook, no expiry,
    out-of-band power, invalid proposal consumes no ID/state.
  - Accept: usable with a fake proposal before Ollama exists.

- [x] **PLOT-04 — Implement event-driven clocks and paired challenge clocks**
  - Depends: PLOT-01
  - Read: plot clocks and no-world-time policy.
  - Create: `src/engine/plot/clocks.py`,
    `tests/unit/engine/test_clocks.py`.
  - Do: match committed typed event predicates, advance bounded authored amount, complete once,
    apply completion effects; paired success/complication completion order; stable processing.
  - Test: matching/nonmatching, +1/capped, completion once, two clocks, paired order, inventory/
    read/wall-clock no trigger, invalid persisted out-of-range rejects.
  - Accept: no system clock import in plot package.

- [x] **PROG-05 — Add party/progression/plot command use cases and API endpoints**
  - Depends: PROG-04, PLOT-04, API-05
  - Read: API boundary and relevant UX panels.
  - Create: `src/engine/progression/use_cases.py`, `src/engine/plot/use_cases.py`,
    `src/api/schemas/{party,progression,plot}.py`,
    `src/api/routes/{party,progression,plot}.py`, integration/API tests.
  - Do: one command/revision per mutation; read endpoints expose view models; mutation routes
    cover membership, upgrade/loadout/fusion, opportunity transitions; milestone/clocks advance
    from committed engine events, not arbitrary client command.
  - Test: each route happy/rejection/stale/duplicate; no client relationship/XP/clock delta;
    one integration scenario recruit -> fight -> XP -> upgrade -> opportunity resolution.
  - Accept: full Milestone 3 checks and updated smoke pass.

---

## Milestone 4 — Local Ollama contracts and orchestration

- [x] **LLM-01 — Add Ollama settings and loopback capability health**
  - Depends: API-01
  - Read: ADR-002, threat model, prompt policy, app/LLM rules.
  - Change: `src/app/config.py`, `.env.example`, health DTO/route.
  - Create: `src/llm/health.py`, `tests/unit/llm/test_ollama_settings_health.py`.
  - Do: require `http` and resolved loopback host for Ollama URL, no userinfo/query/fragment;
    explicit model names; health port reports unreachable/text absent/text available/image
    unknown/available separately. HTTP behavior is fake in tests.
  - Test: IPv4/localhost/IPv6 loopback accepted, remote/redirect target rejected, empty model,
    fake tag responses/timeouts/malformed; health never mutates or downloads.
  - Accept: absence is typed and no cloud endpoint/key setting exists.

- [x] **LLM-02 — Implement bounded Ollama HTTP transport**
  - Depends: LLM-01
  - Read: LLM folder rules and local threat controls.
  - Create: `src/llm/ollama_client.py`, `tests/unit/llm/test_ollama_client.py`.
  - Do: injected `httpx.AsyncClient`; `/api/tags` capability and `/api/chat` structured request;
    connect/read/write/pool timeouts; cancellation; response byte cap while streaming/read;
    reject non-loopback redirects; typed status/JSON/model errors; safe metadata logging only.
  - Test: exact request fixture, success, 4xx/5xx, timeout/cancel, invalid JSON, oversized,
    redirect loopback and remote, missing response field; no test network.
  - Accept: client has no save/game-rule imports and never shells out.

- [x] **LLM-03 — Build bounded action-interpreter context packets**
  - Depends: ACTION-01
  - Read: action prompt context, prompt budget, narrator retrieval inputs.
  - Create: `src/llm/retrieval/{__init__,action_context}.py`,
    `tests/unit/llm/test_action_context.py`.
  - Do: immutable packet from candidate set plus current area/known facts/capability labels/
    protected constraints; stable ranking/order; 12 KiB budget; remove ranked optional
    summaries only; fail if mandatory candidate/reference data exceeds cap.
  - Test: minimal/full, deterministic ordering, hidden facts absent, entire journal absent,
    optional truncation, mandatory overflow, hostile instruction stored as quoted data.
  - Accept: packet contains ordinals, never mutable objects/repository or final DC mapping.

- [x] **LLM-04 — Add safe prompt renderer and versioned action template/examples**
  - Depends: LLM-03, LLMCON-01
  - Read: prompt policy and action prompt spec completely.
  - Create: `src/llm/prompts/{renderer,action_interpreter_v1}.py`,
    `src/llm/prompts/fixtures/action_examples.json`,
    `tests/unit/llm/test_action_prompt.py`.
  - Do: named renderer fails missing/extra values; delimit JSON context and player text as
    data; exact role/contract/rubric; five documented few-shot cases but include at most
    three selected by fixed relevance tags; version `action-interpreter/1.0.0`.
  - Test: golden structural sections/version, delimiter-safe hostile text, no final DC/state
    patch authority, example schemas validate, byte budget.
  - Accept: prompt output is deterministic for same packet/input and logs are not involved.

- [x] **LLM-05 — Implement action interpretation, one repair, and typed failure**
  - Depends: LLM-02, LLM-04
  - Read: LLM contract retry policy and exploration data flow.
  - Create: `src/llm/orchestration/{__init__,action_interpreter}.py`,
    `tests/unit/llm/test_action_interpreter.py`.
  - Do: construct request, call transport, strict parse/version/candidate validation; on schema
    failure one repair using same facts/request ID and bounded invalid output/diagnostics;
    no repair for timeout/unavailable; return proposal or typed failure and safe metrics.
  - Test: valid first, valid repair, two malformed, fabricated ordinal, mismatch version/ID,
    timeout, cancellation, repair facts identical, raw text absent from logs.
  - Accept: implementation satisfies `ActionInterpreter` port and cannot mutate state.

- [x] **LLM-06 — Implement narrator contract, context packet, and prompt**
  - Depends: LLM-02, STATE-04
  - Read: NarrationV1 contract, narrator prompt, save narrative memory.
  - Create: `src/llm/contracts/narration.py`, `src/llm/retrieval/narrator_context.py`,
    `src/llm/prompts/narrator_v1.py`, tests under `tests/{unit,contract}/llm/`.
  - Do: exact contract; packet only committed facts/revision/display roll/style/area/present
    speakers/recent summaries/objective/threat/forbidden claims; 20 KiB budget; prompt version
    `narrator/1.0.0`; escaped/quoted data.
  - Test: contract matrix, hidden facts absent, 3–5 events, unknown speaker ordinal, optional
    truncation/mandatory overflow, prompt hostile text and authority rules.
  - Accept: narration string cannot carry structured effects and packet builds only post-commit.

- [x] **LLM-07 — Implement narration validation, orchestration, and deterministic fallback**
  - Depends: LLM-06
  - Read: narrator rules/fallback and action flow post-commit behavior.
  - Create: `src/llm/orchestration/narrator.py`, `src/llm/orchestration/fallback.py`,
    `tests/unit/llm/test_narrator.py`.
  - Do: one generation plus one formatting repair; validate speakers/fact ordinals and exact
    known forbidden mechanical claims; fallback formatter uses result kind/display entities/
    roll/effects. Narrator error never throws into commit/retries command.
  - Test: valid, malformed repaired, unsupported death/item/location/speaker rejected, timeout,
    fallback for direct/check/combat/rejection, no new roll/state write.
  - Accept: committed factual result remains visible independently of model.

- [x] **LLM-08 — Implement opportunity contract, context, prompt, and planner adapter**
  - Depends: LLM-02, PLOT-03
  - Read: OpportunityProposalV1, opportunity prompt and plot design.
  - Create: `src/llm/contracts/opportunity.py`,
    `src/llm/retrieval/opportunity_context.py`,
    `src/llm/prompts/opportunity_planner_v1.py`,
    `src/llm/orchestration/opportunity_planner.py`, contract/unit tests.
  - Do: exact ordinal-only contract; protected facts/closed candidates; 20 KiB budget; version
    `opportunity-planner/1.0.0`; one repair; hand proposal to deterministic validator, never
    assign ID in adapter.
  - Test: valid/repair, canonical claim nonempty, fabricated/out-of-range ordinals, duplicate
    hook rejected downstream, timeout -> authored fallback/no frontier corruption.
  - Accept: planner fulfills port and has no repository/state mutation imports.

- [x] **LLM-09 — Integrate interpreter/narrator/planner at post-validation boundaries**
  - Depends: LLM-05, LLM-07, LLM-08, API-03, PROG-05
  - Read: all four data flows and component boundaries.
  - Change: app dependencies; action/plot use-case orchestration; health/action responses.
  - Create: `tests/integration/llm/test_llm_action_narration_pipeline.py`.
  - Do: submit raw text -> context/interpreter -> deterministic pipeline; commit -> narrator;
    frontier replenishment calls planner only when engine signals need. Use one long-lived
    client and bounded concurrency. State stores no generated narration.
  - Test: valid direct/check, malformed action no mutation, narrator fail after commit, planner
    invalid fallback, unavailable model 503, duplicate command avoids repeat roll but may return
    stored factual result/fallback, no network through fake transport.
  - Accept: Milestone 4 smoke uses fake model; optional manual Ollama check is separate/skipped.

- [x] **SCRIPT-03 — Add explicit local model setup and capability inspection script**
  - Depends: LLM-02
  - Read: scripts rules, Ollama choice, image capability fallback.
  - Create: `scripts/setup_local_models.py`,
    `tests/integration/scripts/test_setup_local_models.py`.
  - Do: default is read-only capability report via HTTP; `--pull <exact-model>` requires
    explicit flag/confirmation and invokes `ollama pull` as argument list, never shell;
    display disk/network warning; no default model is silently chosen; verify after pull.
  - Test: help/report with fake transport, unavailable CLI, decline/confirm with fake subprocess,
    exact argv, failure exit, remote URL rejected. Normal tests never execute Ollama.
  - Accept: script has no cloud fallback, broad deletion, or API-key request.

---

## Milestone 5 — Campaign builder and immutable publication

- [x] **BUILD-01 — Implement normalized builder brief and draft-state models**
  - Depends: SCHEMA-09
  - Read: builder UX, generation order, source handling.
  - Create: `src/campaign/builder/{__init__,models,normalization}.py`,
    `tests/unit/campaign/test_builder_brief.py`.
  - Do: exact guided fields, Quick Prompt input, content boundaries, source metadata, art
    direction; normalize whitespace/list duplicates; map Quick defaults to same full brief;
    draft stage states `not_started|running|valid|invalid|cancelled` and diagnostics.
  - Test: guided/full, quick defaults, missing premise, custom theme/length requirements,
    content limit, no raw source in normalized summary, extra fields.
  - Accept: neither path can mark a campaign published or skip stages.

- [ ] **BUILD-02 — Implement bounded plain-text source importer**
  - Depends: BUILD-01
  - Read: threat model source controls; worldbuilding source policy.
  - Create: `src/campaign/importers/{__init__,plain_text}.py`,
    `tests/unit/campaign/test_plain_text_importer.py`.
  - Do: accept `.txt`/explicit supported transcript extensions only; injected path already
    rooted by safe picker contract; size/encoding/control-char limits; normalize text; return
    metadata + bounded chunks for design summary. Never parse PDF/HTML/docx in v1.
  - Test: UTF-8 valid, empty, oversized, binary/NUL, wrong extension, symlink escape through
    storage wrapper, embedded prompt injection retained as quoted data, no execution.
  - Accept: unsupported formats return actionable error, not a new dependency.

- [ ] **BUILD-03 — Implement draft filesystem repository**
  - Depends: BUILD-01, CAMP-01
  - Read: campaign context and publish transaction principles.
  - Create: `src/campaign/storage/drafts.py`,
    `tests/integration/campaign/test_draft_repository.py`.
  - Do: safe draft ID directories separate from published campaigns; atomic write each brief/
    stage/diagnostic; expected draft revision; list/load/cancel; never playable through
    CampaignRepository. Use same JSON safety and permissions.
  - Test: create/update/stale/cancel/reload, unsafe path/symlink, interrupted write, published
    loader refuses draft, source document not copied unless explicit bounded import policy.
  - Accept: valid completed stages survive retry/cancel and no partial JSON is authoritative.

- [ ] **BUILD-04 — Define one strict design-generation contract per artifact**
  - Depends: LLM-02, SCHEMA-09, BUILD-01
  - Read: campaign-generation prompt and campaign schema entirely.
  - Create: `src/llm/contracts/campaign_generation.py`,
    `tests/contract/test_campaign_generation_contracts.py`.
  - Do: request/stage enum and typed draft response wrapper around the owning Pydantic root;
    meta/style is the only paired first stage; no monolithic response; publication fingerprint/
    status forbidden or forced draft/null; version/request match.
  - Test: smallest/full per stage, wrong artifact for stage, published/fingerprint attempt,
    extra field, oversized response, monolithic multiple-artifact attempt.
  - Accept: generated artifact can enter existing validation without dict reshaping.

- [ ] **BUILD-05 — Add versioned templates for the seven generation stages**
  - Depends: BUILD-04
  - Read: campaign prompt stages/rubric, prompt policy, worldbuilding document.
  - Create: `src/llm/prompts/campaign_generation_v1.py`, original few-shot fixture files,
    `tests/unit/llm/test_campaign_generation_prompts.py`.
  - Do: one template builder per stage with only needed prior summaries/IDs, exact output
    schema, quoted source chunks, user boundaries, readable skills, protected source facts;
    prompt versions `campaign-<stage>/1.0.0`.
  - Test: required/forbidden context per stage, hostile source delimiter, examples validate,
    no long source reproduction, deterministic same-input prompt, budget failures.
  - Accept: no stage receives whole source/campaign when summaries/typed dependencies suffice.

- [ ] **BUILD-06 — Orchestrate stage generation and bounded repair**
  - Depends: BUILD-03, BUILD-05, VALID-04
  - Read: builder shared pipeline and generation repair rules.
  - Create: `src/campaign/generation/{__init__,stages,orchestrator}.py`,
    `tests/integration/campaign/test_generation_orchestrator.py`.
  - Do: fixed stage order; persist running/result/diagnostics; validate local then cross-stage;
    repair owning artifact only with bounded diagnostics/same facts, max two repair attempts;
    cancel safely; split oversized deterministic ID ranges only via explicit stage plan.
  - Test: all stages valid, local repair, cross-reference repair at owner, exhausted invalid,
    cancel/restart retains valid prior, timeout, no publish, fake transport only.
  - Accept: invalid partial campaign is inspectable draft and never playable.

- [ ] **BUILD-07 — Implement typed review edits and complete validation report**
  - Depends: BUILD-06
  - Read: builder review/validation UX and schema diagnostics.
  - Create: `src/campaign/builder/review.py`,
    `tests/integration/campaign/test_builder_review.py`.
  - Do: edit one owning artifact through typed replacement and expected draft revision; run
    local validation then full validation; maintain sorted errors/warnings; expose reference
    option view. No raw arbitrary JSON patch in v1.
  - Test: valid edit, invalid field/reference, stale edit, fixing error, cross-file diagnostics,
    missing optional art warning not error, publish-ready predicate.
  - Accept: review never silently repairs or changes another artifact.

- [ ] **BUILD-08 — Publish an immutable validated campaign atomically**
  - Depends: BUILD-07, CAMP-02
  - Read: campaign generation publish flow, ADR-003, threat model.
  - Create: `src/campaign/storage/publisher.py`,
    `tests/integration/campaign/test_campaign_publish.py`.
  - Do: require complete error-free draft/user confirmation flag; canonicalize all design
    files; status published/version/fingerprint; stage sibling directory, sync, atomic rename;
    refuse existing campaign ID/version; assets optional; mark draft published only after load
    verifies installed pack.
  - Test: success/load fingerprint, invalid/unconfirmed, same ID, injected failure each step,
    content order stability, draft preserved, no saves created.
  - Accept: published design cannot be edited in place through builder repository.

- [ ] **BUILD-09 — Expose builder draft/generate/review/publish API**
  - Depends: BUILD-08, LLM-09
  - Read: builder UX and API boundary.
  - Create: `src/api/schemas/builder.py`, `src/api/routes/builder.py`,
    `tests/integration/api/test_builder_routes.py`.
  - Do: guided/quick create same brief; stage status/generate/cancel; typed artifact review edit;
    validation report; publish confirmation. Long generation uses bounded local background task
    with polling/cancel in v1, not an external queue/WebSocket requirement.
  - Test: both paths, full fake generation, errors/repair/cancel, stale draft, publish disabled/
    enabled, no client fingerprint/status injection, restart reads persisted stage.
  - Accept: no quick bypass, cloud call, or partially published response.

---

## Milestone 6 — Local React UI

- [ ] **UI-01 — Bootstrap strict React/Vite test project without product screens**
  - Depends: API-01
  - Read: UI context/manual, screen map, accessibility, ADR-008/011.
  - Create: `src/ui/package.json`, `package-lock.json`, `tsconfig*.json`, `vite.config.ts`,
    `eslint.config.js`, `index.html`, `src/{main,App}.tsx`, `src/test/setup.ts`, one App test.
  - Do: React 19, TypeScript 5.x strict, Vite 7.x, Vitest, Testing Library/user-event,
    jest-dom, axe-core integration, ESLint TypeScript/React hooks; Node >=22; scripts `dev`,
    `build`, `typecheck`, `lint`, `test`. App renders only “Storymode setup” landmark.
  - Test: `npm ci`, then lint/typecheck/test/build; zero npm audit runtime high/critical issues
    or document/block dependency choice before proceeding.
  - Accept: lockfile committed, no CDN/analytics/cloud/fonts, tests use jsdom, build output ignored.

- [ ] **UI-02 — Generate API types and implement resilient local fetch client**
  - Depends: UI-01, API-05, PROG-05, BUILD-09
  - Read: API component boundary and UI retry rule.
  - Create: checked-in `src/ui/src/api/schema.d.ts`, `client.ts`, `errors.ts`, `commands.ts`,
    tests; add dev-only OpenAPI type generator script/dependency.
  - Do: generate types from checked-in backend OpenAPI JSON; fetch base is same-origin by
    default; typed JSON/error handling, abort support; UUID command ID created once per user
    intent and retained across transport retry; revision-conflict fetch/reconcile helper.
  - Test: success/error/non-JSON/timeout/cancel/409, retry same ID, new user intent new ID,
    no remote base URL accepted in production config.
  - Accept: no game formulas, `any`, hidden cloud fallback, or direct Ollama call.

- [ ] **UI-03 — Build accessible shell, routing, error boundary, and base styles**
  - Depends: UI-02
  - Read: screen map responsive/nav rules and accessibility entire document.
  - Create: `src/ui/src/routes/*`, `components/AppShell.tsx`, `components/ErrorBoundary.tsx`,
    `styles/{tokens,global}.css`, tests.
  - Do: browser router for documented routes; semantic header/nav/main, skip links, current
    save/revision slot, 360px responsive drawers, visible focus, reduced motion, text sizing;
    safe not-found/unexpected error pages. No generated raw HTML.
  - Test: keyboard navigation/focus, route rendering, 404, error reset, axe, reduced-motion
    CSS assertion and production build.
  - Accept: no placeholder state mutation controls and all routes can render empty state.

- [ ] **UI-04 — Implement startup preflight and campaign library/detail**
  - Depends: UI-03
  - Read: screen map startup and builder/library relevant API.
  - Create: `src/ui/src/features/startup/*`, `features/campaigns/*`, tests.
  - Do: health cards separately show core/storage/text/image; campaign list/detail/validation;
    loading/empty/error/retry; text unavailable blocks only model play/generation; missing image
    warning; links to create/continue/recovery. Display no filesystem paths.
  - Test: all capability combinations, campaign empty/invalid/valid, keyboard/axe, escaped
    malicious title/description, retry.
  - Accept: never offers cloud fallback or calls health repeatedly without user/poll interval cap.

- [ ] **UI-05 — Implement guided and quick builder input flows**
  - Depends: UI-04
  - Read: builder UX guided/shared pipeline.
  - Create: `src/ui/src/features/builder/BriefForm.tsx`, `QuickPromptForm.tsx`, route/state/tests.
  - Do: exact guided fields/bounds and source metadata; quick premise/theme/length/difficulty;
    client convenience validation mirrors only shape; submit same typed draft API; preserve
    user fields on errors; content boundaries and local-only source notice.
  - Test: valid guided/quick request shapes, required/custom fields, invalid source response,
    server 422, keyboard labels/focus/axe, no quick publish action.
  - Accept: API remains authoritative and both flows route to same progress/review.

- [ ] **UI-06 — Implement generation progress, cancellation, diagnostics, and review**
  - Depends: UI-05
  - Read: builder generation/review/publish UX.
  - Create: builder `GenerationProgress`, `ValidationReport`, artifact review forms/tabs,
    publish confirmation components and tests.
  - Do: bounded polling with cleanup; exact stage/attempt/model/elapsed/cancel; sorted diagnostic
    file/pointer/code; typed owning-artifact edits with draft revision; reference selectors;
    publish disabled on errors, optional art warning, immutable confirmation.
  - Test: stage transitions/retry/cancel/unmount, edit valid/invalid/stale, diagnostic focus link,
    warning vs error, publish confirmation/success/failure, keyboard/axe.
  - Accept: no raw writable JSON editor and valid prior stages remain visible.

- [ ] **UI-07 — Implement exploration log, context rail, and free-text composer**
  - Depends: UI-04, LLM-09
  - Read: exploration UX and accessibility result order.
  - Create: `src/ui/src/features/exploration/{ExplorationScreen,NarrativeLog,ContextRail,
    ActionComposer,ResultCard}.tsx` plus tests/styles.
  - Do: render authoritative area/party/objective/opportunities/clocks; escaped narration and
    factual cards; composer char limit/status; exact submission state machine; same command ID
    retry/status reconciliation; invalid/partial UI and confirmation.
  - Test: idle/loading/rejected/partial/direct/transport unknown/model 503/narrator fallback,
    duplicate-click prevention, malicious text escaped, log focus/live behavior, axe.
  - Accept: no state inferred from prose and opening rail/panels sends no mutation.

- [ ] **UI-08 — Implement visible check confirmation, luck, and roll history**
  - Depends: UI-07
  - Read: exploration visible check, difficulty/luck, roll schema.
  - Create: exploration `CheckPanel`, `RollResult`, `RollHistory` and tests.
  - Do: display exact formula/DC/stakes/luck from API; Roll/Cancel; retain resolve command ID
    on timeout and query state; result order raw/modifiers/total/DC/band/effects; reroll linkage;
    optional cosmetic animation after result only and reduced-motion skip.
  - Test: each band, modifiers including negative, all luck availability/actions, cancel, timeout
    retry same ID, double click, reduced motion, keyboard/focus/live/axe.
  - Accept: UI never generates die/random animation value or recomputes outcome.

- [ ] **UI-09 — Implement character, inventory, party, journal, and save panels**
  - Depends: UI-07, PROG-05
  - Read: progression/party/save design and screen map.
  - Create: `src/ui/src/features/{character,inventory,party,journal,saves}/*` and tests.
  - Do: read authoritative resources/stats/skills/fusions/items/equipment/relationships/events;
    bounded outside-combat loadout/upgrade/fusion/party mutations; five manual+autosave slots;
    disable exact server-reported reasons; no clock advance on open.
  - Test: empty/full, upgrade/loadout/fusion prerequisites and server rejection, party max/unavailable,
    save list/create conflict, open sends GET only, combat disables changes, keyboard/axe.
  - Accept: mechanics are descriptions/data from API, not calculations duplicated in UI.

- [ ] **UI-10 — Implement combat screen and all bounded commands**
  - Depends: UI-08, API-05
  - Read: combat UX and accessibility result order.
  - Create: `src/ui/src/features/combat/*` and tests.
  - Do: remove exploration composer; encounter/turn order/resources text+bars; server-allowed
    skill/target review, Defend, contextual Flee/Yield confirmation; base vs effect-die result;
    factual log; soft consequence/game-over view; stable command retry/reconciliation.
  - Test: hero/companion turn, disabled reasons, target rules, base-only/all bonus bands, Defend,
    flee/yield allowed/denied, victory/soft defeat/game-over, double/timeout, keyboard/focus/axe.
  - Accept: no free-text combat route and no client-computed mana/damage/order/reward.

- [ ] **UI-11 — Implement save recovery and global accessibility/manual test record**
  - Depends: UI-09, UI-10, SAVE-04
  - Read: save recovery UX policy and accessibility manual matrix.
  - Create: `src/ui/src/features/saves/RecoveryScreen.tsx`, tests, and
    `docs/ux/accessibility-test-record.md`.
  - Do: show corruption/orphan/derived/snapshot diagnostics; choose validated snapshot and
    explicit restore confirmation; preserve original notice; focus/results. Run keyboard-only,
    VoiceOver, 200% zoom, 360px, reduced motion, and color-independent manual checks.
  - Test: no valid snapshot, select/confirm/success/failure, no automatic restore, axe; record
    date/browser/OS/result/known issue for manual checks without claiming unrun checks.
  - Accept: all automated UI checks/build pass and genuine manual evidence is recorded.

---

## Milestone 7 — Local image capability, security, and release polish

- [ ] **IMAGE-01 — Define image capability/result and deterministic asset keys**
  - Depends: LLM-02, BUILD-08
  - Read: image prompt policy, threat model, campaign assets context.
  - Create: `src/llm/contracts/image.py`, `src/campaign/assets/{__init__,keys,prompts}.py`,
    tests.
  - Do: typed capability/result metadata; canonical prompt from style + entity summary; SHA-256
    key includes model/version capability, prompt version/text, dimensions, style/entity IDs;
    engine-owned relative destination. No gameplay/save facts.
  - Test: key stability/difference for every component, path-safe entity, prompt positive/
    negative structure, hidden/player data absent, unsupported dimensions/MIME.
  - Accept: no image generated/analyzed and no model filename accepted.

- [ ] **IMAGE-02 — Implement optional local generation adapter and validated cache install**
  - Depends: IMAGE-01
  - Read: Ollama/image capability rules and threat controls.
  - Create: `src/llm/orchestration/image_generator.py`,
    `src/campaign/assets/{cache,queue}.py`, tests.
  - Do: use detected installed Ollama image capability only; bounded single-worker queue and
    cancellation; byte/dimension/MIME-signature validation; temp+fsync+atomic cache install;
    sidecar metadata; dedupe same key; typed unavailable/failure.
  - Test: fake success/cache hit/dedupe, unavailable, timeout/cancel, oversized, MIME spoof,
    bad dimensions, interrupted install, model output cannot escape asset root.
  - Accept: missing image never blocks campaign/play and no cloud/subprocess fallback.

- [ ] **IMAGE-03 — Add deterministic fallback cards and asset API**
  - Depends: IMAGE-02, API-05
  - Read: image fallback and accessibility alt rules.
  - Create: `src/campaign/assets/fallback.py`, `src/api/schemas/assets.py`,
    `src/api/routes/assets.py`, tests.
  - Do: fallback metadata/theme derived deterministically from campaign style/entity type;
    serve allowlisted cached image IDs with safe headers or fallback descriptor; enqueue only
    authenticated-by-local-state known area/enemy asset; no arbitrary prompt/path endpoint.
  - Test: cache/fallback, missing/invalid entity, traversal, content type/CSP/nosniff, enqueue
    dedupe, play with unavailable image model.
  - Accept: asset bytes are presentation only and response includes accessible description.

- [ ] **IMAGE-04 — Render backgrounds/portraits with equivalent fallback and alt text**
  - Depends: IMAGE-03, UI-10
  - Read: exploration/combat visual and accessibility rules.
  - Create/change: UI scene background/enemy portrait/fallback components and tests.
  - Do: lazy load local asset, show themed CSS/SVG fallback descriptor on absent/error, use
    concise contextual alt or decorative empty alt, never block action UI or shift focus.
  - Test: image success/fail/unavailable, fallback labels/style, decorative/context alt, no
    remote URL, keyboard/axe/reduced-data-friendly behavior.
  - Accept: identical gameplay functionality with images disabled.

- [ ] **SEC-01 — Run the complete local-boundary adversarial test matrix**
  - Depends: IMAGE-03, BUILD-09, LLM-09
  - Read: threat model every control.
  - Create: focused `tests/integration/security/` modules; change code only for discovered bugs.
  - Do: cover traversal/absolute/symlink, oversized/deep/duplicate JSON, malformed JSONL,
    malicious HTML, imported/model prompt injection, non-loopback URLs/redirects, timeouts,
    malformed/oversized responses/images, unsafe filenames, CORS/host defaults, safe errors/logs.
  - Test: `uv run pytest tests/integration/security -q` plus full suite.
  - Accept: every required threat-model verification has a named passing test; no skipped case
    without a documented platform reason and manual evidence.

- [ ] **CI-02 — Add frontend and schema/smoke checks to CI**
  - Depends: UI-11, IMAGE-04, SEC-01, BOOT-04
  - Read: README commands and ADR dependencies.
  - Change: `.github/workflows/test.yml`.
  - Do: retain least permissions/pinned actions; backend job runs lock/scaffold/schema/Ruff/mypy/
    tests/smoke; frontend job installs declared Node, `npm ci`, lint/typecheck/test/build. Cache
    only package-manager downloads with lockfile keys; no Ollama/models/secrets.
  - Test: run every command locally from clean dependency installs where practical; inspect YAML.
  - Accept: CI requires no cloud product service beyond GitHub runner dependency download.

- [ ] **POLISH-01 — Add resource limits, cancellation, and observability verification**
  - Depends: CI-02
  - Read: prompt budgets, threat availability controls, builder/image UX.
  - Create: `tests/integration/test_resource_limits.py`; update docs/config only as necessary.
  - Do: assert all input/context/output/file/count/depth/concurrency/timeouts have named settings
    with safe maxima; cancellation leaves no authoritative partial state/draft/image; logs contain
    IDs/versions/timing/size/result but no raw prompt/source/save/path secrets.
  - Test: limit boundaries and capture/redact logs for action/narrator/builder/image/save errors.
  - Accept: no unbounded collection/model request/background job in a reachable v1 flow.

- [ ] **POLISH-02 — Execute release checklist and update canonical status**
  - Depends: POLISH-01
  - Read: every definition-of-done section, README, changelog, root context.
  - Change: `README.md`, `CONTEXT.md`, `CHANGELOG.md`, relevant folder docs; create
    `docs/release-checklist.md` with actual evidence.
  - Do: clean install; all backend/frontend/schema/scaffold/security/smoke checks; validate valid/
    invalid campaign; save round-trip/recovery; deterministic run without Ollama; manual local
    Ollama text run if installed; image unavailable fallback; accessibility record. State exact
    skipped manual conditions and never call them passed.
  - Accept: docs no longer say documentation-only, every claim links to command evidence, and
    smallest next product task is selected through a new ADR/checklist—not improvised here.

---

## Milestone gates

After each milestone, stop and report using root `AGENT.md`'s handoff format. A milestone
is complete only when every item within it is checked and these common gates pass:

```bash
uv run python scripts/check_scaffold.py
uv run python scripts/generate_schemas.py --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests scripts
uv run pytest
uv run python scripts/run_smoke_test.py
```

After `UI-01`, also run:

```bash
npm --prefix src/ui run lint
npm --prefix src/ui run typecheck
npm --prefix src/ui run test
npm --prefix src/ui run build
```

Commands whose creating slice is not yet checked are **not available**, not “passing.”

## Questions intentionally deferred to evidence, not implementer taste

These do not block the documented vertical slices. Keep prototype defaults until the
named research/playtest work produces evidence:

- final enemy power coefficients and encounter target ranges;
- exact XP threshold numbers in the first real campaign;
- local model names and hardware recommendations;
- whether post-v1 desktop packaging uses Tauri or another option;
- whether supported image generation is exposed by the user's installed Ollama/model.

Changing a prototype default requires the relevant research summary, tests, design doc,
and ADR when architectural.
