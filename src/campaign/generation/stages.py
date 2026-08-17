"""Individual campaign stage executors with bounded repair (BUILD-06).

Guarantees:
- Executes typed generation prompts against local Ollama client.
- Bounded repair: up to 2 repair attempts per stage on schema or parsing errors.
- Never regenerates valid prior stages; records structured diagnostics.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from campaign.builder.models import (
    DraftStage,
    DraftStageState,
    DraftState,
    StageDiagnostic,
)
from campaign.storage.drafts import DraftRepository
from llm.ollama_client import ChatMessage, OllamaClient
from llm.prompts.campaign_generation_v1 import (
    render_stage_repair_prompt,
)

MAX_STAGE_REPAIR_ATTEMPTS: int = 2


class StageExecutionError(Exception):
    """Raised when a generation stage fails or exhausts repair attempts."""


class StageRunner:
    """Executes and repairs individual campaign generation stages."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        draft_repo: DraftRepository,
        model_name: str = "llama3.1:8b",
    ) -> None:
        self.ollama_client = ollama_client
        self.draft_repo = draft_repo
        self.model_name = model_name

    async def execute_stage(
        self,
        stage: DraftStage,
        draft: DraftState,
        contract_cls: type[BaseModel],
        prompt_generator: Callable[[], str],
        context_summary: str,
    ) -> DraftState:
        """Execute a generation stage with up to 2 repair attempts on failure."""
        current_state = draft.stages.get(
            stage, DraftStageState(stage=stage, status="running", attempts=0)
        )
        if current_state.status == "valid":
            return draft

        # Mark stage running
        running_stages = dict(draft.stages)
        running_stages[stage] = current_state.model_copy(
            update={"status": "running", "attempts": current_state.attempts + 1}
        )
        updated_draft = self.draft_repo.save_draft(
            draft.model_copy(update={"stages": running_stages}),
            expected_revision=draft.revision,
        )

        attempts = 0
        prompt = prompt_generator()
        last_raw_response = ""
        last_diagnostics: list[str] = []

        while attempts <= MAX_STAGE_REPAIR_ATTEMPTS:
            attempts += 1
            try:
                chat_res = await self.ollama_client.chat(
                    model=self.model_name,
                    messages=[ChatMessage(role="user", content=prompt)],
                    format_json=True,
                )
                last_raw_response = chat_res.message.content

                # Validate JSON directly against stage contract
                validated = contract_cls.model_validate_json(last_raw_response)

                # Success!
                stage_data: dict[str, Any] = validated.model_dump(mode="json")
                stage_result = DraftStageState(
                    stage=stage,
                    status="valid",
                    attempts=attempts,
                    diagnostics=[],
                    artifact_data=stage_data,
                )
                final_stages = dict(updated_draft.stages)
                final_stages[stage] = stage_result
                return self.draft_repo.save_draft(
                    updated_draft.model_copy(update={"stages": final_stages}),
                    expected_revision=updated_draft.revision,
                )

            except (json.JSONDecodeError, ValidationError, ValueError) as e:
                diag_msg = str(e)
                last_diagnostics.append(diag_msg)
                if attempts <= MAX_STAGE_REPAIR_ATTEMPTS:
                    # Prepare repair prompt
                    prompt = render_stage_repair_prompt(
                        stage=stage,
                        invalid_json=last_raw_response,
                        diagnostics=[diag_msg],
                        context_summary=context_summary,
                        request_id=f"req-repair-{stage}-{attempts}",
                    )
            except Exception as e:
                # Fatal transport or network error
                last_diagnostics.append(f"Transport error: {e}")
                break

        # Failed after attempts
        diag_objs = [
            StageDiagnostic(stage=stage, code="STAGE_FAILED", message=d, is_error=True)
            for d in last_diagnostics
        ]
        failed_stage = DraftStageState(
            stage=stage,
            status="invalid",
            attempts=attempts,
            diagnostics=diag_objs,
            artifact_data=None,
        )
        final_stages = dict(updated_draft.stages)
        final_stages[stage] = failed_stage
        return self.draft_repo.save_draft(
            updated_draft.model_copy(update={"stages": final_stages, "diagnostics": diag_objs}),
            expected_revision=updated_draft.revision,
        )
