"""LLM orchestration package for action interpretation, narration, and opportunity planning."""

from llm.orchestration.action_interpreter import (
    ActionInterpreter,
    FailureReason,
    InterpretationFailure,
    InterpretationResult,
    InterpretationSuccess,
)
from llm.orchestration.fallback import generate_deterministic_fallback_narration
from llm.orchestration.narrator import NarratorOrchestrator
from llm.orchestration.opportunity_planner import OpportunityPlannerAdapter

__all__ = [
    "ActionInterpreter",
    "FailureReason",
    "InterpretationFailure",
    "InterpretationResult",
    "InterpretationSuccess",
    "NarratorOrchestrator",
    "OpportunityPlannerAdapter",
    "generate_deterministic_fallback_narration",
]
