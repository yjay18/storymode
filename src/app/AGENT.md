# Application Agent Rules

- Keep `create_app()` side-effect free until lifespan begins; tests must construct it
  with fake settings/dependencies.
- Validate resolved data paths and loopback URLs. Never add cloud endpoint/key config.
- Wire one instance of random source and repositories; do not instantiate them inside
  routes or rule functions.
- Startup capability failures are typed health states, not process crashes unless the
  local data root is unsafe/unusable.
- Tests: configuration defaults/rejections, dependency override, startup/shutdown, and
  no-network-on-import. Update root setup/run docs when commands change.
