# Scripts Context

Scripts are thin local operator entry points. Planned commands set up/check local
models, validate a campaign, migrate a copied save, and run a deterministic smoke
flow. Reusable logic belongs in source modules; scripts parse arguments, call it, and
render safe diagnostics/exit codes.
