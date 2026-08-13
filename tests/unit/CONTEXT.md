# Unit Test Context

Unit tests exercise one pure model/rule/state machine/orchestrator with injected scripted
dependencies. They must be fast, deterministic, filesystem-free except explicit temp
input helpers, and independent of test order.
