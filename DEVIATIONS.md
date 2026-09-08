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

### PLAY-01 — no served save-list route; health path; thin save response

**Original spec:** PLAY-01 lists the served play paths and says to mirror them field for
field, deleting hand-invented types.

**Deviations:**
- The UI client had `listSaves` → `GET /api/v1/campaigns/{id}/saves`, which the backend
  never serves (the campaigns router has no `/saves`). `listSaves` and `SaveSlotSummary`
  were removed and `CampaignDetail` dropped its saved-games list; it now only loads the
  campaign detail and offers "New Hero" to create a save.
- `getHealth` targeted `/api/v1/health`, but the health router is mounted at `/health`.
  Fixed to `/health` (not an `/api/v1` path, so the drift test does not cover it).
- The real `SaveSummaryResponse` is thin (no HP/mana/attributes/inventory/skills, no
  `in_combat`/`active_combat_id`). `ContextRail` now renders name/area/difficulty/slot from
  it; the exploration screen's combat-redirect was removed (PLAY-03 owns combat
  reachability). `CharacterPanel` and `InventoryPanel` (both unmounted today) were repointed
  at `PlayerProgressionView` from `GET .../progression`; the real contract has no attribute
  block, so attribute rendering was dropped.
- `ExplorationScreen.onCancel` now calls `POST /api/v1/actions/cancel-check` instead of only
  clearing local state, so the persisted pending check is actually cancelled. The richer
  error handling (503 banner, 409 refetch/retry, full roll breakdown) remains for PLAY-02.
- A `CampaignDifficulty` type alias for `DefaultDifficulty` was kept so the out-of-scope
  builder forms compile without edits.

### PLAY-02 — roll "total" equals the die

**Original spec:** the result card shows "raw die, modifiers, total, DC, band".

**Deviation:** the engine (`engine/actions/resolution.py`) compares the raw d20 directly to
`final_dc`; the situational modifiers are baked into the DC via `difficulty_adjustment`,
not added to the roll, and `ResolveCheckResponse` exposes only `roll` and `band`. The
breakdown therefore shows Total = Die, lists the named modifiers (which adjusted the DC),
and shows Base DC + adjustment = Final DC. This mirrors the actual mechanic rather than
inventing a roll-side total the contract does not carry.

### PLAY-03 — CampaignDetail extended with areas/encounters (backend)

**Original spec:** PLAY-03 says the context rail lists "the current area's `encounters`
(from the campaign detail)" and lists only UI files in its Change set; the milestone rule
says the backend routes/schemas are the contract and the UI should match them.

**Deviation (user-authorised):** the served `CampaignDetail` exposed only `area_count`, so
no endpoint carried encounter IDs and combat was unreachable from the UI. With the user's
explicit approval, `CampaignDetail` gained `areas: list[CampaignAreaView]`, each with its
`encounters` (`id`, `enemy_archetype_ids`, `condition`) — the minimal data the play loop
needs to call `POST /combat/start`. Contract test added in
`tests/integration/api/test_campaign_save_routes.py::test_get_campaign_detail`; documented
in `docs/ux/combat-ui.md`. This is an additive, backward-compatible response change.

Also: the combat route lost its `:combatId` segment (`/play/{c}/{s}/combat`) since combat
is keyed by save, matching `GET /combat/view?campaign_id&save_id`.

### PLAY-04 — no XP threshold or fusion-recipe data in the contract

**Original spec:** the character panel shows "XP to next threshold" and Fusion "lists
recipes whose conditions are met".

**Deviation:** `ProgressionViewResponse` exposes `xp` and `upgrade_tokens` but no level
threshold, and no served endpoint lists fusion recipes. Computing a threshold client-side
would be the forbidden client-side rule logic, so the panel shows level, raw XP, and
tokens; the Fusion section is a read-only placeholder ("No eligible fusion recipes") until
recipe data is served. Upgrade and loadout post their routes and render the returned
`player` view (and the server's typed error message on rejection), with no client-side
rule logic. The panel is a self-contained container (fetches its own progression) and is
not yet mounted in a play screen — that wiring is outside PLAY-04's listed files.

### PLAY-05 — extra test file touched; num_predict heuristic

**Original spec:** PLAY-05 lists `test_generation_orchestrator.py` and `test_schema_hints.py`
as the test changes.

**Deviation:** `tests/integration/campaign/test_campaign_publish.py` also had to change — its
`_build_full_valid_draft` helper packed skills+items+enemies+balance into one `skills` stage,
which no longer assembles a full pack after the split. It now builds the three stages. This
was a required consequence of the stage split, not a new feature.

The per-stage `num_predict` bound is a heuristic (`max(2048, min(8192, len(skeleton)))`,
tokens sized from the skeleton character length) marked with a `ponytail:` comment and a
tuning note; it is a fail-fast cap, not a tuned generation budget. PLAY-06 live evidence
should confirm no legitimate stage response is truncated by it.

### Live model evidence

**Original spec:** No slice ran a prompt against a real model; all 577 tests use `httpx.MockTransport`.

**Resolution:** `tests/live/` holds opt-in tests gated by `STORYMODE_LIVE_OLLAMA=1` and the `live_ollama` marker. CI does not run them. `scripts/generate_campaign.py` produces the bundled sample campaign through the real pipeline.

### PLAY-06 — live verification run (2026-09-02, qwen3.5:9b, Apple Silicon)

User-authorised live run. Results:

- **Live tests (`make live`): 2 of 3 pass.**
  - `test_configured_model_is_installed` — PASS.
  - `test_meta_style_stage_produces_valid_artifact` — PASS (stage 1 validates against the
    real model).
  - `test_interpreter_and_narrator_round_trip` — **FAIL (422)**. The action interpreter
    rejects the model's proposal with `Request ID mismatch: expected 'act-cmd-live-1', got
    'act-search-room-1'`. The interpreter (`llm/orchestration/action_interpreter.py:100`)
    requires the model to echo `packet.request_id` verbatim, but the interpreter prompt
    (`llm/prompts/action_interpreter_v1.py`) never instructs it to, so qwen3.5:9b invents
    an id. Pre-existing (LLM-04), outside Milestone 8's changed files. **Fixed as a
    follow-up (see below).**

- **Full generation (`make generate`): stalls at stage 2.** meta_style validates on the
  first attempt; `rules` (WorldStageResponse) fails all 3 attempts because the model omits
  the required `world.factions[].relationship_edges` field on one faction. Model-compliance
  reliability on the WorldFile contract, non-deterministic, unrelated to the PLAY-05 stage-6
  split (stages 1-5 are unchanged). No pack published in this run. (A direct
  `scripts/generate_campaign.py --draft <id>` resume is the documented recovery, but the run
  environment's classifier only permits the `make` targets.)

- **Browser walk: not completed.** No freshly generated pack published, and the free-text
  "look"/"check" path is blocked by the same interpreter request_id issue. The mechanical
  combat path (engage → skill → defend → yield) does not depend on the interpreter and is
  covered by `scripts/run_smoke_test.py` and the PLAY-03 Vitest suite against real response
  shapes.

**Assessment:** the Milestone 8 wiring verified where the model permits — routes reachable
with correct 503/422 envelopes, stage-1 generation valid, and the split pipeline publishes a
`load_campaign`-valid pack in the mocked all-stages test. The two live failures are
pre-existing model-compliance gaps outside this milestone's scope; PLAY-06 is left unchecked
pending either a larger/more-compliant model (e.g. the installed `qwen3.8`) or the
generation follow-up.

### Follow-up fix — interpreter treats request_id as server-owned (small-model support)

**Why:** the PLAY-06 live run showed the action interpreter 422-ing every free-text action
because the small model (qwen3.5:9b) did not echo the packet's `request_id`, and the prompt
never asked it to. This made the browser play loop unusable with small local models.

**Change (`src/llm/orchestration/action_interpreter.py`):** `_validate_and_parse_proposal`
now assigns the packet's authoritative `request_id` to the proposal instead of rejecting on
mismatch, and the `REQUEST_ID_MISMATCH` failure reason was removed. This is a synchronous
single-response call, so the reply can only belong to this request; the correlation field is
server-owned and no longer depends on untrusted model output. Contract-version,
prompt-version, and candidate-ordinal validations are unchanged — no safety check was
weakened. Test `test_interpret_action_request_id_mismatch` was rewritten to
`test_interpret_action_assigns_server_request_id` (asserts success + server id assigned).
Backend gates green (585 passed). Not weakening: the guard verified nothing the server did
not already own; the fix makes correlation authoritative rather than advisory.

**Follow-up 2 — scalar→list coercion in `parse_llm_response`.** With request_id fixed, the
live round trip surfaced the next small-model quirk: qwen3.5:9b emitted
`capability_mentions: "skill-1"` (a bare string) where the contract wants a list. The parser
now wraps a scalar into a one-element list for the proposal's list fields (`entity_mentions`,
`capability_mentions`, `stakes`) before strict validation; the result is still validated, so
genuinely malformed output still fails. Contract test added.

**Live re-verification (qwen3.5:9b): all three live tests pass** (`3 passed in ~131s`). The
interpret → resolve → narrate round trip completes with a small model. The live test's
free-text prompt was also corrected to reference the `Object` that exists in the
`minimal-campaign` fixture — the previous "search the room" prompt referenced an entity
absent from the fixture, which the engine's world-reference validation correctly rejects
(`No candidate found for 'room'`) regardless of model size. That rejection surfaced as a
`422 validation_error`; whether an unresolvable entity reference should instead degrade to
an in-world redirect (per `docs/ux/exploration-ui.md`) is an engine/route concern for a
separate slice, not a small-model or interpreter issue.

**Generation** still stalls at stage 2 with qwen3.5:9b (model omits a required WorldFile
field); unchanged by these interpreter fixes and still recommended for a bigger model
(`qwen3.8`) or a generation-robustness slice.

### Follow-up 3 — generation robustness: schema-driven list coercion

**Why:** the PLAY-06 generation run stalled at stage 2 because qwen3.5:9b dropped the
required `world.factions[].relationship_edges` list on one faction, failing all 3 attempts.
Same class as the interpreter quirks — small models drop or scalarize list fields.

**Change (`src/campaign/generation/stages.py`):** `coerce_to_contract_schema` walks the
stage contract's JSON schema and, before strict validation, fills every missing/null
array-typed field with `[]` and wraps a scalar into a one-element list — at any nesting
depth. Only arrays are touched: missing required scalars/objects still fail (no content is
fabricated beyond empty lists), and the result is still validated with
`model_validate_json`, so the strict contract still governs. Applied in `execute_stage`
before validation. Not run against a live model (user deferred that); verified with mocks:
a unit test on the coercion and a stage-runner test that feeds `world.json` with a
faction's `relationship_edges` removed and asserts the `rules` stage now validates with the
field defaulted to `[]`. Backend gates green (588 passed).

**Ceiling:** this makes a dropped list an empty list rather than a hard failure, so a model
that omits *content* produces a thinner-but-valid draft; cross-file validation at review and
publish still catches a hollow world, and drafts are editable before publish. It does not
help when a model omits a required scalar/object — those still fail the stage.

### Follow-up 4 — live generation iteration with qwen3.5:9b (2026-09-02)

User-authorised live generation run (`make generate`, qwen3.5:9b). Iterating stage by stage
(resuming the same draft, so completed stages are cached), robustness was added until each
stage passed:

- **Stages 1-4** (meta_style, rules, areas, plot) now validate. `rules` previously stalled on
  a dropped `relationship_edges` list — fixed by the schema-driven list coercion (Follow-up 3).
- **areas** truncated mid-JSON under the old skeleton-sized `num_predict` (it capped ~2k tokens
  while areas needs ~3.5k). The cap was widened.
- **characters** failed because a companion's `starting_loadout` referenced a skill absent from
  its `starting_skill_ids`. Added `normalize_stage_semantics`: drop loadout entries a companion
  does not know (conservative — no fabricated knowledge). Companions now validate.
- **skills** was the bottleneck: qwen3.5:9b rambled to ~40k chars (a legitimate skills file is
  ~24.8k), produced unterminated JSON, and the third attempt **timed out** — generating toward
  a 12,288-token cap at ~6.6 tok/s exceeds a 30-min timeout. Two fixes: (a) recalibrated the cap
  to `max(4096, min(8192, len(skeleton)*6))` so the largest legitimate stage (~8k tokens) fits
  under the timeout; (b) tightened the skills prompt (`campaign-skills/1.1.0`) to exactly 4
  combat + 3 non-combat skills, one base_effect per level, `effect_die` null, small trees —
  cutting output size sharply. `num_ctx` is 24576 to fit the large late-stage prompt plus output.
- Added `make generate DRAFT=<id>` to resume a stalled draft without redoing completed stages.

**Not completed to publish:** the user chose to stop before another model run, so items_enemies
and balance were not exercised live and no pack was published this session. The stalled draft
(`draft-dc88f606`) has stages 1-5 valid and is resumable with
`STORYMODE_MODEL_TEXT=qwen3.5:9b STORYMODE_OLLAMA_TIMEOUT_SECONDS=1800 make generate DRAFT=draft-dc88f606`.
All fixes are covered by mocked tests; backend gates green (588 passed).

### Follow-up 5 — mount the character panel in the play screen (2026-09-08)

**Why:** the PLAY-04 entry above records that `CharacterPanel` was built but "not yet mounted
in a play screen — that wiring is outside PLAY-04's listed files". It stayed unreachable in
the browser, so progression (level, XP, tokens, loadout, upgrade) could not be exercised in
the PLAY-06 walk even though `docs/ux/exploration-ui.md` lists character among the screen's
utility panels. User-requested; not a checklist slice.

**Change (`src/ui/src/features/exploration/ExplorationScreen.tsx`):** the panel is rendered
in the right-hand utility rail beside `ContextRail` and `RollHistory` (the rail already hosts
one utility panel, and the doc lists both there). It is a self-contained container, so it
needs only `campaignId`/`saveId`. Two consequences:

- `key={state.revision}` — every committed action bumps the save revision, which remounts the
  panel and re-reads `GET .../progression`. Without it the panel would show mount-time HP, XP,
  and tokens forever while the narrative log reported damage and rewards. React's own remount
  key rather than new refresh plumbing; the cost is one loopback GET and a brief "Loading
  character..." per committed action.
- The rail widened from 280px to 340px so a skill row (`name (Lv n)` plus Upgrade and Equip)
  fits without wrapping. The shell is 1400px, so the narrative column keeps ~1020px.

`ContextRail` was left untouched, so the player name now appears twice in the rail — once in
the save block (name/difficulty/slot/revision) and once as the character sheet heading. Two
framed cards with different subjects; deduplicating means editing a PLAY-03 file for
cosmetics, so it was not done.

`InventoryPanel` is still unmounted — the request was the character panel only.

**Test:** `ExplorationScreen.test.tsx` gains "mounts the character sheet and re-reads it when
the save revision changes" (asserts the panel renders level/tokens/skill from the mocked
progression, then that a committed action triggers a second `getProgression`). Verified it
fails with the `key` removed. The two existing tests now wait on the area id instead of the
player name, which the mounted panel made ambiguous. Gates green: backend 588 passed,
3 skipped; UI lint/typecheck/48 tests/build.

### PLAY-08 — one existing test asserted the old status

**Original spec:** the slice lists `test_action_routes.py` under Change.

**Deviation:** `test_invalid_target_returns_422` asserted exactly the behaviour this slice
reverses. It was renamed to `test_unresolvable_mention_returns_in_world_rejection` and
rewritten to assert `200` + `rejection_reason` + an unchanged revision, rather than being
deleted. No other test covered the rejection status.

The `campaign_integrity` branch (the save's area missing from the pack) keeps `422` and has
no dedicated route test — reaching it needs a save and pack that disagree, which no fixture
builds. The engine-level branch is covered by the existing use-case tests.

### PLAY-10 — no packed campaign authors a fusion recipe

**Original spec:** the slice's route contract test asserts eligibility against the served
pack.

**Deviation:** neither `tests/fixtures/campaigns/valid-minimal` nor the bundled
`campaigns/salt-ledger` authors a single `fusion_recipes` entry, so a test against the
shared fixture would have looped over nothing and asserted only the envelope. The slice
adds a second client fixture (`client_with_recipe`) that copies the minimal campaign and
injects three combat skills, a catalyst reference, and one valid recipe — enough to pass
cross-file reference validation — and asserts the served `blocked_reason`. The shared
fixture was left alone so no other test's counts shift, and it keeps a test asserting the
empty case.

The panel treats the fusion list as supplementary: it is fetched alongside progression but
a failure leaves the section empty rather than blanking the character sheet, since the
sheet's primary data is progression.

`salt-ledger` authoring real fusion recipes is campaign content, not a code slice.

### PLAY-11 — the inventory panel is presentational, so it is nested, not mounted beside

**Original spec:** the slice says to mount `InventoryPanel` in the utility rail beside the
character sheet, keyed on the save revision, "matching how `CharacterPanel` is mounted".

**Deviation:** that assumed `InventoryPanel` was a self-fetching container like
`CharacterPanel`. It is not — it takes a `player: PlayerProgressionView` prop and renders it.
Mounting it in the rail would have meant either a second fetch of the same `progression`
endpoint or new plumbing in `ExplorationScreen` to fetch and refresh progression for it.

`CharacterPanel` already holds exactly that payload, so it renders
`<InventoryPanel player={player} />` at the end of its own section instead: one import and
one line, no extra request, and it inherits the revision keying that already keeps the
character sheet fresh. Both panels keep their own `aria-label`, so they remain separately
addressable; `InventoryPanel` and its test are untouched.

Consequence: the inventory is not shown when progression fails to load. They are the same
payload, so there is nothing to show in that case anyway.
