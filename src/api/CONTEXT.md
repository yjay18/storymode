# API Context

`api` is a versioned local HTTP adapter. `schemas/` owns request/response DTOs and
`routes/` delegates to injected use cases. v1 routes are under `/api/v1`; health is
separate and reports deterministic core, storage, text model, and image capability.

Mutation DTOs carry `command_id` and `expected_revision`. Responses carry committed
revision, typed result/error, and server-computed allowed next actions. Routes contain
no dice, damage, point-buy, reference, persistence, or prompt logic.
