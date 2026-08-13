# Source Agent Rules

- Implement only the selected checklist slice; create package files when that slice
  requires them, not placeholder classes ahead of use.
- Read the target module context/manual and governing design/schema documents.
- Add deterministic tests before rule code and contract tests before adapters.
- Use typed models/results/errors; avoid dictionaries past transport/JSON boundaries.
- Do not print, call network/filesystem, read environment, generate IDs, read clocks,
  or consume randomness from pure domain/rule functions.
- All public functions and methods require type annotations and focused docstrings for
  non-obvious invariants. Run Ruff, mypy, and relevant Pytest targets.
