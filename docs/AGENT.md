# Documentation Agent Rules

- Edit only documents whose governed contract is in the selected checklist slice.
- Preserve stable terminology from `docs/schemas/`; do not invent synonyms for IDs,
  states, or event names.
- Use normative words precisely: **must** is required, **may** is optional, and
  **should** needs a documented reason when violated.
- Put architecture choices in the decision log, mechanics in game design, serialized
  fields in schemas, and model instructions in prompts.
- A rule change must name affected source modules and tests.
- Do not paste full source files or duplicate root context into child documents.
- Verify every link and update `CHANGELOG.md` for public behavior changes.
