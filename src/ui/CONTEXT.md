# UI Context

`ui` will be a React/TypeScript/Vite single-page client. It consumes `/api/v1`, renders
authoritative state, maintains only presentation/transient request state, and uses the
screen/state behavior in `docs/ux/`.

Planned structure: `src/api/` typed client, `src/components/`, `src/features/` by
screen/domain, `src/routes/`, `src/state/` for server-query/request coordination,
`src/styles/`, and colocated tests. No backend-generated prose is rendered as raw HTML.
