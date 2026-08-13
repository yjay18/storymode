# Plot and Opportunity Graph

## Campaign spine

Published milestones are a directed graph. Each milestone has stable ID, canonical
truth, narrative purpose, required outcomes, allowed approaches, forbidden changes,
preconditions, valid next IDs, and pacing/difficulty metadata. Validation requires
known references, at least one start, at least one reachable ending, and no required
milestone unreachable from all starts. Cycles must be explicitly flagged and bounded.

Canonical truth and required outcomes are protected. Runtime systems may reveal,
delay, approach, or apply consequences around a milestone but never change what it
means.

## Opportunity frontier

A save tracks opportunities separately from design. Normally 3–7 are `active`; a
temporary count below three is allowed only when the campaign is ending or no valid
proposal can be generated, and must produce diagnostics rather than invalid content.

Each opportunity has ID, parent milestone ID, origin (`authored` or `runtime`), title,
referenced established entity IDs, allowed outcomes, preconditions, expiry conditions,
balance rating, and one state:

- `active`: visible and presently actionable;
- `deferred`: still possible but not currently presented;
- `locked`: known but conditions are unmet;
- `invalidated`: a committed event made every allowed route impossible;
- `resolved`: a defined allowed outcome was committed.

Unchosen opportunities are deferred, never deleted due to non-selection. Invalidation
requires a named committed fact and a deterministic predicate. Transformation creates
a new successor referencing the predecessor; audit history remains.

## Runtime proposal validation

A model proposal must attach to one current/reachable parent milestone, use only IDs
from its supplied candidate set, preserve forbidden/protected facts, contain no new
world law/faction/major entity/revelation/mechanic, fit a validated power/pacing band,
and define expiry plus allowed outcomes. The engine assigns the runtime opportunity
ID after validation.

## Clocks

Clocks have stable ID, integer current value, positive maximum, visibility, trigger
event predicates, and completion effects selected from an authored allowlist. Only a
committed matching event advances a clock, normally by one unless an explicit rule
defines another bounded amount. Reading, inventory management, dialogue display, and
wall-clock time never advance clocks.

Multi-step social, stealth, investigation, technical, and medical scenes may pair a
success clock with a complication clock. Completion order determines only authored
outcomes. A model may narrate pressure but cannot increment a clock.
