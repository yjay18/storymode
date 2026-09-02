# Source Context

`src/` will contain the application implementation. It is currently a directory-only
scaffold; no source package is claimed runnable. Backend modules are top-level Python
packages under `src/`; `src/ui` is a separate TypeScript project.

Dependency direction is UI/API/adapters -> application/engine -> domain. The domain
and deterministic engine are testable without FastAPI, filesystem access, or Ollama.
