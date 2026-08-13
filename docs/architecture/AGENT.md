# Architecture Agent Rules

- Architecture changes require an ADR before implementation.
- Keep diagrams and module names synchronized with `src/` vertical context files.
- Describe failure, recovery, ownership, and test seams—not only happy paths.
- Do not introduce a second process, database, network service, or state owner in v1.
- Run architecture-link checks when they exist and the full relevant test suite for
  any architecture-affecting code change.
