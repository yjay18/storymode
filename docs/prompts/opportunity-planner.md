# Opportunity Planner Prompt Specification

## Role

Propose one local route attached to an existing reachable milestone using only
supplied candidate entities, predicates, outcomes, and approach tags. It cannot create
canonical truth, IDs, mechanics, or state.

## Context packet

Include protected parent milestone summary and forbidden changes, current area,
established present/reachable entity candidates, relevant facts/flags, authored
outcome/predicate candidates, active/deferred opportunity summaries, pacing/difficulty
target, and style excerpt. Exclude hidden milestone revelations not needed for the
route and unrelated global lore.

## Quality rubric

A proposal should provide a concrete actionable hook, at least two plausible supplied
approach tags where available, a meaningful local consequence, an explicit expiry
condition, and new framing without duplicating an active opportunity. It must not
solve the parent milestone automatically or invalidate another route by assertion.

## Validation and fallback

The engine resolves ordinals, assigns ID, validates graph/references/balance/frontier,
and rejects protected-truth changes. On failure it may request one repair with exact
diagnostics. If still invalid, defer generation and use an authored opportunity; do
not lower constraints merely to keep the frontier at three.
