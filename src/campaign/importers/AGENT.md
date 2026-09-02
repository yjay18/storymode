# Campaign Importer Agent Rules

- Enforce safe rooted paths, extension, bytes, encoding, control characters, and chunk caps.
- Never execute/render markup, follow embedded paths, or reproduce whole source in campaign.
- Unsupported formats return a typed error; do not add parser dependencies opportunistically.
- Test binary/NUL/oversize/symlink/injection inputs and ensure no network/process execution.
