# Test Agent Rules

- Add the failing focused test before deterministic implementation.
- Inject scripted random values, fixed UTC clock, deterministic ID sequence, temp data
  roots, fake model ports, and in-memory/fake repositories as appropriate.
- Assert exact state/events/rolls and that rejected commands leave input unchanged.
- Each invalid fixture must name and assert its intended error code/pointer; a failure
  for an unrelated reason is not success.
- Do not loosen assertions, snapshot volatile timestamps/paths, call real network, or
  skip tests solely to complete a slice.
- Integration writes use Pytest temporary directories, never repository campaigns.
