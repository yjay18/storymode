# Domain Models Context

This folder owns strict Pydantic value, campaign-definition, runtime-state, audit, and
root models. Models enforce local shape/range/intra-object invariants. Cross-file ID,
graph, campaign/state binding, and balance validation belong to engine validation.

Definitions are frozen. Runtime transitions build and validate a new root instead of
leaving partially mutated state. Field names/types come only from `docs/schemas/`.
