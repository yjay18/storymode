# Game Design Research Summary

## Current evidence status

External research is intentionally not part of this setup-only change. The following
are product hypotheses derived from the supplied bootstrap brief, not research claims:

- Freeform input needs deterministic entity/capability validation to preserve agency
  without granting authorial control.
- Guaranteed combat base effects fit text pacing better than repeated attack misses.
- Protected milestones plus a bounded opportunity frontier balance coherence and
  local flexibility.
- Visible arithmetic and immutable roll audits support player trust.
- Fail-forward outcomes protect campaign momentum better than clue-gated dead ends.

## Research slices before balance lock

1. Compare at least three shipped text-heavy RPGs on action feedback, log readability,
   failure consequences, and combat pacing; capture concrete UI/mechanic patterns.
2. Compare point-buy/DC probability curves across authoritative tabletop rules and
   calculate Story/Normal/Hard outcome rates for representative modifiers.
3. Review accessibility guidance and shipped keyboard/screen-reader patterns for
   narrative logs, turn order, and dice results.
4. Playtest the deterministic CLI slice without Ollama, then with a small local model;
   record invalid-action rate, ambiguous-reference rate, context size, and latency.

## Decision gates

Do not tune the documented DC bands, near-miss width, mana costs, damage, recovery,
enemy power coefficients, or context/frontier size from taste alone. Keep current
values as explicit prototype defaults; change them only with probability analysis or
playtest evidence and an ADR/design update.
