# Data Flow

## Exploration action without a check

1. UI submits raw text, `command_id`, `save_id`, and `expected_revision`.
2. API validates transport size/shape and creates `SubmitExplorationAction`.
3. Engine loads campaign definitions and the validated save snapshot.
4. Context builder selects the current area, present entities, inventory capability
   tags, current milestone/opportunities, active clocks, and recent factual memory.
5. Ollama returns an `ActionProposal`. It is parsed with a strict Pydantic contract.
6. Entity resolver maps mentions to visible/known stable IDs. Ambiguous or absent
   references are rejected or converted to a bounded search attempt.
7. Rules validate location, ownership, availability, capability, world law, plot
   protection, allowed outcomes, and whether uncertainty has meaningful stakes.
8. If no roll is justified, pure rules produce a state transition and factual event.
9. Save repository commits the new revision atomically.
10. Narrator receives only the committed facts and a bounded context packet.
11. UI receives committed state summary and narrated text, or deterministic fallback.

The model never sees a mutable repository and never supplies a state patch.

## Exploration action with a visible check

Steps 1–7 are identical. The engine then creates a `PendingCheck` with immutable
action ID, formula components, semantic difficulty, engine-selected DC, possible
outcome bands, and source revision. It commits that pending check without rolling.

The UI displays the check. On confirmation it sends `ResolvePendingCheck` with a new
command ID and expected revision. The engine verifies the pending check, requests
exactly one d20 from the secure roller, computes the band, produces roll/event/state
records, clears the pending check, and commits. A retry of the same command ID must
return the recorded outcome without another roll.

## Combat command

1. UI renders allowed commands supplied by the engine; it does not infer them.
2. API submits selected action/skill and target IDs with expected revision.
3. Engine validates actor turn, combat phase, mana, status, target, and encounter
   permissions.
4. Guaranteed base damage/effect applies. Exactly one effect die is rolled only when
   the skill definition requires it.
5. Engine applies armour-before-HP, statuses, defeat consequence, mana regeneration,
   and deterministic next-actor selection.
6. Repository commits state, event, and roll records; narration is optional and later.

## Campaign generation

The builder runs ordered stages: inputs -> meta/style -> world/factions -> areas and
characters -> skills/items/enemies -> plot/balance -> reference validation -> graph
validation -> balance validation -> user review -> immutable publish. Each stage
accepts typed prior outputs and produces a versioned draft artifact. A failed stage
does not publish partial design as playable content.

Published campaign files are content-hashed into a canonical fingerprint. Creating
the first save binds it to that fingerprint. Editing a published pack requires a new
campaign version and an explicit compatibility/migration decision.

## Save transaction and crash recovery

For transition to revision `N+1`:

1. Acquire the per-save lock and confirm disk revision is `N`.
2. Validate complete next state and all journal/roll records in memory.
3. Append prepared records tagged `revision=N+1` and `transaction_id`; flush and
   `fsync` their files.
4. Write `state.json.<transaction_id>.tmp` in the save directory, flush, `fsync`,
   re-read, and validate.
5. `os.replace` the temporary file onto `state.json`; `fsync` the directory where
   supported. This replacement is the commit point.
6. Refresh derived `narrative_memory.json` and `save_meta.json` atomically. Failure
   here does not invalidate authoritative state and is repairable.
7. Release the lock, then request narration.

On load, records above the authoritative state revision are uncommitted preparations.
Recovery reports and quarantines or marks them abandoned; it never treats them as
committed facts. Missing derived files are rebuilt from authoritative state and the
committed journal. A saved state is never reconstructed from narrator prose.

## Read data

Read endpoints return explicit view models and may omit secret/internal fields.
They do not mutate state, advance clocks, consume randomness, or call Ollama merely
because a user opens a screen.
