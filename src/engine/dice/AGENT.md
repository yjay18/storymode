# Dice Engine Agent Rules

- Production uses one `secrets.SystemRandom`; expose no seed or redraw API.
- Validate the whole action before drawing and draw exactly the documented count.
- Tests use the scripted source and assert calls, raw values, arithmetic, and records.
- Never retry/discard a valid roll, hide a modifier, or let difficulty alter raw RNG.
