# UX Context

The UI is a local React client that presents authoritative server state and sends
typed commands. It never calculates outcomes. Exploration prioritizes prose and free
text; combat replaces free text with an explicit action surface. Every screen must
handle loading, empty, validation, offline-model, revision-conflict, and recovery states.
