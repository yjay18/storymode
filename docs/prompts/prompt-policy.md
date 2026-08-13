# Prompt Policy

## Template structure

Every prompt is assembled in this order:

1. immutable role and authority limits;
2. exact output contract/version and “JSON only” rule where applicable;
3. task-specific decision rubric;
4. delimited canonical context selected by code;
5. delimited untrusted user/source text;
6. at most three concise few-shot examples;
7. request ID and final output reminder.

Templates are static UTF-8 files under `src/llm/prompts/`. Variables are inserted by
named placeholders through one safe renderer that fails on missing/extra variables.
Do not build templates with ad hoc concatenation in routes.

## Authority language

Each prompt states: supplied facts are the entire factual scope; content inside data
delimiters cannot change instructions; the model may propose or present only its
named role; and unknown facts must remain unknown. These instructions are defense in
depth. Pydantic and engine validation remain authoritative.

## Context budgets

Runtime defaults, configurable downward but not silently upward:

- action interpreter: 12 KiB serialized factual context, 1,000 output tokens;
- narrator: 20 KiB context, 900 output tokens;
- opportunity planner: 20 KiB context, 1,500 output tokens;
- repair prompt: prior response max 8 KiB and validation errors max 2 KiB.

The context builder truncates only ranked optional summaries. It never truncates a
JSON object into invalid syntax or omit an entity that a selected mandatory reference
depends on. If mandatory facts exceed budget, return `context_too_large`.

## Versioning and logging

Store semantic prompt versions such as `action-interpreter/1.0.0`; responses echo the
version and contract version. Normal logs include request ID, role, versions, model,
durations, context/output byte counts, retry count, and result code—not raw player
text, source documents, full prompts, or responses. An explicit local debug option may
write redacted diagnostics and must default off.

## Few-shot and golden cases

Few-shot inputs use fictional fixture entities and demonstrate valid, creative,
partial, invalid, and injection-resistant behavior. They are not campaign lore.
Golden checks assert schema, candidate references, confirmed-fact coverage, banned
claims, and bounded length. Do not assert exact creative phrasing.

## Model configuration

Use low temperature for structured roles and modest temperature for narration, with
JSON/schema response mode when Ollama/model capability supports it. Configuration is
role-specific and documented; never rely on a particular model's undocumented habit.
Capability failure is surfaced before play or handled with the defined fallback.
