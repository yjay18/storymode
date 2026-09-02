# Campaign Context

`campaign` owns design-time creation and immutable campaign-pack access:

- `builder/`: draft state and user review workflow;
- `importers/`: bounded untrusted local source extraction;
- `generation/`: staged model generation and repair coordination;
- `assets/`: optional local image queue/cache and deterministic fallback metadata;
- `storage/`: safe paths, canonical JSON, load/publish/fingerprint repositories.

Drafts are not playable. Publish occurs only after individual schema, cross-reference,
graph, and balance validation and assigns a fingerprint. Runtime saves never mutate
published design.
