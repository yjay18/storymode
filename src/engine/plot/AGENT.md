# Plot Engine Agent Rules

- Use only closed typed predicates/effects; never evaluate strings or narrator claims.
- Defer unchosen opportunities; invalidate only from a named committed predicate.
- Runtime proposals reference existing candidates and receive IDs only after validation.
- Clocks react to committed events, never wall time/UI reads.
- Test reachability, every state transition, frontier bounds, and stable event order.
