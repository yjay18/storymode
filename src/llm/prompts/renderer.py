"""Safe deterministic prompt template renderer (LLM-04)."""

from __future__ import annotations

import re
from typing import Any


class PromptRenderError(Exception):
    """Raised when template rendering fails due to missing or extra variables."""


_PLACEHOLDER_REGEX = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def render_template(template: str, variables: dict[str, Any]) -> str:
    """Render a named template string, strictly enforcing required and disallowed variables.

    Raises PromptRenderError if:
    - Any placeholder in the template is not present in `variables`.
    - Any key in `variables` is not a placeholder in `template`.
    """
    placeholders = set(_PLACEHOLDER_REGEX.findall(template))
    provided_keys = set(variables.keys())

    missing = placeholders - provided_keys
    if missing:
        raise PromptRenderError(
            f"Missing required template variable(s): {', '.join(sorted(missing))}"
        )

    extra = provided_keys - placeholders
    if extra:
        raise PromptRenderError(
            f"Unexpected extra template variable(s): {', '.join(sorted(extra))}"
        )

    result = template
    for key, val in variables.items():
        placeholder = f"{{{key}}}"
        result = result.replace(placeholder, str(val))

    return result
