# Campaign Storage Agent Rules

- Resolve validated IDs below an injected root; reject traversal/absolute/symlink escape.
- Enforce duplicate-key, depth, count, and byte limits before constructing models.
- Follow exact save/publish transaction order and test injected failure at every boundary.
- Never silently repair, overwrite newer revision, edit published design, or delete only copy.
- Use temporary test roots and keep filesystem/platform behavior isolated behind helpers.
