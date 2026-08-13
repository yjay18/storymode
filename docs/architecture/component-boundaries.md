# Component Boundaries

## Allowed dependency matrix

| From | May depend on | Must not depend on |
|---|---|---|
| `domain` | standard library, Pydantic | FastAPI, filesystem, HTTP, Ollama, UI |
| `engine` | `domain`, its own ports | FastAPI, concrete storage, Ollama client, UI |
| `campaign` | `domain`, campaign ports | API/UI, engine internals, mutable LLM state |
| `llm` | `domain` read DTOs, LLM ports | save repositories, engine mutation services |
| `api` | app use cases, transport schemas | rule calculations, direct file I/O, Ollama |
| `app` | all backend adapters for wiring | player-visible mechanics |
| `ui` | generated/manual API contract | filesystem, Python internals, Ollama direct |

Imports are checked with a lightweight architecture test added in `ARCH-01`.

## Ports to define before adapters

- `RandomSource.roll(sides: int) -> int`
- `Clock.now_utc() -> datetime` for audit metadata only
- `IdGenerator.new(prefix: str) -> str`
- `CampaignRepository.load/publish/list`
- `SaveRepository.load/commit/list/recover`
- `ActionInterpreter.propose(context, text) -> ActionProposal`
- `Narrator.narrate(context, confirmed_outcome) -> Narration`
- `OpportunityPlanner.propose(context) -> OpportunityProposal`
- `ImageGenerator.generate(prompt, destination) -> AssetResult`

Protocols live inward, concrete adapters outward. DTOs passed through ports must be
immutable or treated as values. No port exposes a Pydantic model's mutable internals.

## Rule ownership

- Stat costs/modifiers and skill/fusion prerequisites: `domain/rules`.
- Check necessity, DC mapping, action validity, and fail-forward band: `engine/actions`.
- Roll creation and arithmetic: `engine/dice`.
- Combat state machine and calculations: `engine/combat`.
- XP, leveling, skill upgrades/fusion: `engine/progression`.
- Milestone/opportunity/clocks: `engine/plot`.
- Cross-file schema/reference/balance checks: `engine/validation` for generic checks,
  coordinated by `campaign` for design packs.
- Persistence transaction orchestration: `engine/state` ports and transition types;
  filesystem details in concrete storage adapters.

No rule may exist only in a route, React component, prompt, or prose formatter.

## Transport contract

Routes are versioned under `/api/v1`. Mutation requests carry `command_id` and
`expected_revision`; responses carry `save_id`, committed `revision`, typed result,
and allowed next actions. HTTP mapping is consistent:

- 400 malformed transport input;
- 404 unknown campaign/save/resource that the caller may address;
- 409 stale revision, duplicate command mismatch, or invalid state transition;
- 422 well-formed command rejected by deterministic rules;
- 503 required local Ollama capability unavailable;
- 500 unexpected internal failure with a safe correlation ID.

Domain errors do not contain HTTP status codes.

## Model contract

LLM adapters accept compact, serializable context models and return one of the
strict contracts in `docs/schemas/llm-contracts.md`. They cannot return executable
code, file paths, SQL, state patches, raw dice, final DCs, or arbitrary entity IDs.
Retries correct formatting only and may not broaden facts. At most two repair
attempts are allowed before a deterministic failure/fallback.

## Frontend contract

The UI displays server-supplied authoritative state and allowed commands. It may
perform convenience validation but never decides success, damage, costs, inventory,
turn order, or opportunity state. Every mutation handles loading, typed rejection,
revision conflict, and retry-with-same-command-ID behavior.
