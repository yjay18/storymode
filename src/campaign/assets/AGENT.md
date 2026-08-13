# Campaign Assets Agent Rules

- Engine selects paths/filenames; validate root containment, MIME signature, size/dimensions.
- Deduplicate by full canonical key and install via temp/fsync/atomic replacement.
- One bounded worker initially; cancellation leaves no installed partial asset.
- No cloud fallback, gameplay inference from images, or player/save secrets in prompts.
- Test missing capability, spoof/oversize/path attacks, interruption, and fallback equivalence.
