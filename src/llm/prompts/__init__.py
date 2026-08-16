"""Prompt rendering and versioned prompt templates (LLM-04, LLM-06, LLM-08)."""

from llm.prompts.action_interpreter_v1 import (
    ACTION_INTERPRETER_PROMPT_VERSION,
    render_action_interpreter_prompt,
    select_action_examples,
)
from llm.prompts.narrator_v1 import (
    NARRATOR_PROMPT_VERSION,
    render_narrator_prompt,
)
from llm.prompts.opportunity_planner_v1 import (
    OPPORTUNITY_PLANNER_PROMPT_VERSION,
    render_opportunity_prompt,
)
from llm.prompts.renderer import PromptRenderError, render_template

__all__ = [
    "ACTION_INTERPRETER_PROMPT_VERSION",
    "NARRATOR_PROMPT_VERSION",
    "OPPORTUNITY_PLANNER_PROMPT_VERSION",
    "PromptRenderError",
    "render_action_interpreter_prompt",
    "render_narrator_prompt",
    "render_opportunity_prompt",
    "render_template",
    "select_action_examples",
]
