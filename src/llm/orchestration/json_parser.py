"""JSON parser for LLM responses."""

import json
import re

from llm.contracts.action import ActionProposal

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

def parse_llm_response(text: str) -> ActionProposal:
    """Parse an LLM response to extract an ActionProposal.
    
    Looks for a JSON code block. Rejects the response if the block is missing
    or there are multiple ambiguous blocks. Validates the JSON strictly.
    """
    matches = _JSON_BLOCK_RE.findall(text)
    
    if not matches:
        # Check if the whole text is just a JSON object without markdown
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            json_str = text
        else:
            raise ValueError("No JSON block found in response")
    elif len(matches) > 1:
        raise ValueError("Multiple JSON blocks found in response, ambiguous")
    else:
        json_str = matches[0]
        
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON: {e}") from e
        
    if not isinstance(data, dict):
        raise ValueError("Parsed JSON is not an object")
        
    return ActionProposal.model_validate(data)
