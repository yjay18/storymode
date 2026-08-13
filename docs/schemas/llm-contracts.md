# LLM Contracts

LLM responses are untrusted JSON parsed with Pydantic `extra="forbid"`. The adapter
extracts one JSON object only; Markdown fences, surrounding prose, multiple objects,
NaN, duplicate keys, unknown fields, and oversized output are rejected. The engine
never deserializes a model-supplied Python object or executes returned content.

Every request includes `contract_version`, `prompt_version`, and a bounded candidate
set. Every response echoes those two versions and a request ID. The adapter rejects
mismatches.

## `ActionProposalV1`

- `contract_version: Literal[1]`
- `prompt_version: str`
- `request_id: str`
- `status: valid | valid_creative | partial | invalid`
- `operation: investigate | alter_environment | use_item | persuade | deceive |
  intimidate | avoid_detection | travel | talk | inspect | search | prepare |
  exploration_attack | other`
- `verb: str` (1–80)
- `entity_mentions: list[EntityMention]` (0–8)
- `capability_mentions: list[str]` (0–8)
- `intended_effect: str` (1–300; semantic only)
- `challenge_label: none | easy | standard | difficult | expert | exceptional |
  near_impossible`
- `uncertainty_reason: str | null` (max 300)
- `stakes: list[str]` (0–5, each max 160)
- `reinterpretation: str | null` (required for `partial`)
- `redirect: str | null` (required for `invalid`)

`EntityMention` contains exact `text`, semantic `role`, and optional
`candidate_ordinal`, which indexes only the supplied candidate list. A model cannot
return arbitrary stable IDs. The resolver validates ordinal and text compatibility.
The proposal contains no DC, modifier, die, result, state patch, loot, new entity,
relationship delta, damage, or final outcome.

## `NarrationV1`

- `contract_version`, `prompt_version`, `request_id`
- `narration: str` (1–2,500)
- `dialogue: list[DialogueLine]` (0–12) where speaker must be from supplied allowed IDs
- `referenced_fact_ordinals: list[int]` pointing to confirmed supplied facts

Narration is display-only and never parsed into effects. The validator rejects unknown
speaker ordinals and text containing known forbidden mechanical claims that contradict
the fact packet. If semantic contradiction cannot be proven safely, the UI labels
narration non-authoritative and state remains the source of truth. Malformed or
unavailable narration uses an engine-authored deterministic template.

## `OpportunityProposalV1`

- common versions/request ID
- `parent_milestone_ordinal`
- `title`, `description`
- `entity_ordinals` (existing candidate entities only)
- `approach_tags` (closed campaign list)
- `allowed_outcome_ordinals` (campaign-defined outcome candidates)
- `precondition_ordinals` (known predicate candidates)
- `expiry_condition_ordinals`
- `challenge_label`, `pacing_reason`
- `canonical_claims: []` must be the empty list in v1

The engine assigns ID and state only after structural, reference, protected-truth,
balance, and frontier validation.

## Design-stage proposals

Campaign generation has one contract per published design artifact, derived from the
campaign Pydantic models but with `status=draft` and no engine-calculated fingerprint,
power rating acceptance, stable runtime IDs, or publication fields. IDs proposed at
design time pass normalization, uniqueness, and cross-stage validation. Generate one
artifact/stage at a time; never accept a monolithic campaign response.

## Image request/result

The model receives a plain prompt assembled from art direction plus a validated area
or enemy description. The adapter result is `{capability, mime_type, bytes, width,
height, model_name}`; filename/destination comes from the engine, never the model.
Only allowlisted image formats and configured byte/dimension bounds are accepted.

## Retry policy

Attempt 1 uses the normal prompt. On syntax/schema failure, attempt 2 sends only the
contract, validation diagnostics, prior invalid response within a strict size bound,
and the same factual candidate set. A final optional repair attempt is allowed only
for campaign design stages, not runtime commands. Retries cannot change request ID,
facts, or candidate scope. Exhaustion returns a typed failure; it never relaxes schema.

## Contract test matrix

For each contract test: smallest valid, full valid, missing required field, extra
field, wrong version, invalid enum, oversized list/text, multiple JSON objects,
Markdown wrapper, fabricated candidate ordinal, prohibited mutation/DC/die field,
and repair exhaustion. Narrator tests also include unknown speaker and unsupported
death/item/location claims.
