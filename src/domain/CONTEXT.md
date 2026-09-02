# Domain Context

`domain` owns stable Pydantic models, enums/value objects, pure invariant functions,
port-neutral services, and typed events. It knows no FastAPI, filesystem, HTTP, Ollama,
or React details.

Planned layout:

- `models/`: campaign/runtime/LLM-facing value contracts split by bounded concept;
- `rules/`: point buy, modifiers, bounded arithmetic, status/effect primitives;
- `services/`: pure cross-model domain policies only when one model cannot own them;
- `events/`: typed event/effect unions and domain error codes.

Models validate local shape. Cross-file/reference/graph checks belong to validation
services so loading one file does not require the entire campaign.
