# Domain Services Agent Rules

- Create a service only when a selected checklist slice names it or existing pure
  domain logic demonstrably spans model boundaries.
- Document inputs, outputs, invariant owner, and why a rule module is insufficient.
- Keep it stateless and free of adapter/config/framework imports.
- Add focused pure unit tests and update the owning canonical design document.
