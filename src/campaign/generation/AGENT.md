# Campaign Generation Agent Rules

- Use the documented stage order/dependency packet and exact artifact contract.
- Retain valid prior stages; never request a monolithic/regenerate-all response.
- Bound attempts/context/output and persist diagnostics/cancellation safely.
- Cross-stage errors route to the field's owning artifact only.
- Tests use fake model transport and cover repair exhaustion/restart/no-publish.
