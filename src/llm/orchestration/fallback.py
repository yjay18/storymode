"""Deterministic fallback narrative generator (LLM-07).

Guarantees:
- Always succeeds and produces valid narrative prose without network or model calls.
- Preserves committed factual results, dice roll summaries, and location grounding.
- Zero state mutations and zero dice rolls.
"""

from __future__ import annotations

from llm.retrieval.narrator_context import NarratorContextPacketV1


def generate_deterministic_fallback_narration(packet: NarratorContextPacketV1) -> str:
    """Generate deterministic factual narrative text from a post-commit context packet."""
    summary = packet.safe_result_summary.strip()
    if not summary:
        summary = f"Action resolved ({packet.result_kind})."

    # If an authoritative dice check was part of this event, prepend the check outcome
    if packet.roll_display is not None:
        roll = packet.roll_display
        dc_str = f" vs DC {roll.target_dc}" if roll.target_dc is not None else ""
        roll_header = f"[{roll.outcome.upper()} Check: {roll.total}{dc_str}]"
        return f"{roll_header} {summary}"

    return summary
