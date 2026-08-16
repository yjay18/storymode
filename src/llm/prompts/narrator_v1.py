"""Narrator prompt templates and renderer (LLM-06)."""

from __future__ import annotations

from llm.ollama_client import ChatMessage
from llm.retrieval.narrator_context import NarratorContextPacketV1

NARRATOR_PROMPT_VERSION = "narrator/1.0.0"

_NARRATOR_SYSTEM_PROMPT = (
    "You are the authoritative Narrator for the Storymode text RPG.\n"
    "Your role is to bring authoritative, already-committed game events to life with rich, "
    "immersive descriptive prose.\n\n"
    "### CONTRACT & RULES\n"
    "1. Strict Factual Grounding:\n"
    "   - You MUST faithfully describe the event in <COMMITTED_EVENT> and its outcome.\n"
    "   - You DO NOT roll dice, alter results, or declare actions successful if the event failed.\n"
    "2. Forbidden Mechanical Claims:\n"
    "   - Obey all forbidden_claims in <NARRATOR_CONTEXT> strictly.\n"
    "   - Never invent deaths, injuries, item gains, or uncommitted location changes.\n"
    "3. Present Speakers & Dialogue:\n"
    "   - Only speakers listed in present_speakers may speak in dialogue.\n"
    "   - Record all speaker ordinals used in 'speaker_ordinals_used'.\n"
    "4. Output Contract:\n"
    "   - Output ONLY valid JSON conforming to NarrationV1:\n"
    "     {\n"
    '       "contract_version": 1,\n'
    f'       "prompt_version": "{NARRATOR_PROMPT_VERSION}",\n'
    '       "request_id": "<from context>",\n'
    '       "narration": "<your vivid narrative text>",\n'
    '       "speaker_ordinals_used": [1, 2],\n'
    '       "fact_ordinals_referenced": []\n'
    "     }\n"
)

_NARRATOR_USER_PROMPT = (
    "<NARRATOR_CONTEXT>\n"
    "{context_json}\n"
    "</NARRATOR_CONTEXT>\n\n"
    "<COMMITTED_EVENT>\n"
    "{event_summary}\n"
    "</COMMITTED_EVENT>\n\n"
    "Narrate the committed event according to the style and rules. "
    "Output ONLY valid NarrationV1 JSON."
)


def render_narrator_prompt(packet: NarratorContextPacketV1) -> list[ChatMessage]:
    """Render the multi-message prompt for the Narrator."""
    context_json = packet.model_dump_json(indent=2)
    user_content = _NARRATOR_USER_PROMPT.format(
        context_json=context_json,
        event_summary=packet.safe_result_summary,
    )

    return [
        ChatMessage(role="system", content=_NARRATOR_SYSTEM_PROMPT),
        ChatMessage(role="user", content=user_content),
    ]
