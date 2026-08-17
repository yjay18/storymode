"""Campaign generation pipeline orchestrator (BUILD-06).

Guarantees:
- Runs generation stages in strict dependency order.
- Skips already valid stages; persists draft state on every transition.
- Halts safely on stage failure without mutating prior completed artifacts.
"""

from __future__ import annotations

from campaign.builder.models import (
    ALL_DRAFT_STAGES,
    DraftStage,
    DraftStageState,
    DraftState,
)
from campaign.generation.stages import StageRunner
from campaign.importers.compactor import WorldCodex
from campaign.storage.drafts import DraftRepository
from domain.models.common import EntityId
from llm.contracts.campaign_generation import (
    AreasStageResponse,
    CharactersStageResponse,
    MetaStyleStageResponse,
    PlotStageResponse,
    SkillsStageResponse,
    WorldStageResponse,
)
from llm.prompts.campaign_generation_v1 import (
    render_meta_style_prompt,
)


class GenerationOrchestrator:
    """Orchestrates the multi-stage campaign generation pipeline."""

    def __init__(
        self,
        stage_runner: StageRunner,
        draft_repo: DraftRepository,
    ) -> None:
        self.stage_runner = stage_runner
        self.draft_repo = draft_repo

    async def generate_stage(
        self,
        draft_id: EntityId | str,
        stage: DraftStage,
        codex: WorldCodex | None = None,
    ) -> DraftState:
        """Run a single generation stage with prompt selection and bounded repair."""
        draft = self.draft_repo.load_draft(draft_id)

        if stage == "meta_style":
            return await self.stage_runner.execute_stage(
                stage="meta_style",
                draft=draft,
                contract_cls=MetaStyleStageResponse,
                prompt_generator=lambda: render_meta_style_prompt(
                    draft.brief, codex=codex, request_id=f"req-gen-meta-{draft.revision}"
                ),
                context_summary=(
                    f"Campaign Title: {draft.brief.title}, Premise: {draft.brief.premise}"
                ),
            )
        elif stage == "rules":
            return await self.stage_runner.execute_stage(
                stage="rules",
                draft=draft,
                contract_cls=WorldStageResponse,
                prompt_generator=lambda: (
                    f"Generate Stage 2 World & Rules JSON for '{draft.brief.title}'."
                ),
                context_summary="Stage 2 World Generation",
            )
        elif stage == "areas":
            return await self.stage_runner.execute_stage(
                stage="areas",
                draft=draft,
                contract_cls=AreasStageResponse,
                prompt_generator=lambda: f"Generate Stage 3 Areas JSON for '{draft.brief.title}'.",
                context_summary="Stage 3 Areas Generation",
            )
        elif stage == "plot":
            return await self.stage_runner.execute_stage(
                stage="plot",
                draft=draft,
                contract_cls=PlotStageResponse,
                prompt_generator=lambda: f"Generate Stage 4 Plot JSON for '{draft.brief.title}'.",
                context_summary="Stage 4 Plot Generation",
            )
        elif stage == "characters":
            return await self.stage_runner.execute_stage(
                stage="characters",
                draft=draft,
                contract_cls=CharactersStageResponse,
                prompt_generator=lambda: (
                    f"Generate Stage 5 Characters JSON for '{draft.brief.title}'."
                ),
                context_summary="Stage 5 Characters Generation",
            )
        elif stage == "skills":
            return await self.stage_runner.execute_stage(
                stage="skills",
                draft=draft,
                contract_cls=SkillsStageResponse,
                prompt_generator=lambda: f"Generate Stage 6 Skills JSON for '{draft.brief.title}'.",
                context_summary="Stage 6 Skills Generation",
            )
        elif stage == "review":
            # Review stage evaluates all prior stages
            all_valid = all(
                st.status == "valid" for name, st in draft.stages.items() if name != "review"
            )
            review_state = DraftStageState(
                stage="review",
                status="valid" if all_valid else "invalid",
                attempts=1,
                diagnostics=[],
                artifact_data=None,
            )
            final_stages = dict(draft.stages)
            final_stages["review"] = review_state
            return self.draft_repo.save_draft(
                draft.model_copy(update={"stages": final_stages}),
                expected_revision=draft.revision,
            )
        return draft

    async def generate_all(
        self,
        draft_id: EntityId | str,
        codex: WorldCodex | None = None,
    ) -> DraftState:
        """Execute all campaign generation stages sequentially."""
        current_draft = self.draft_repo.load_draft(draft_id)

        for stage_name in ALL_DRAFT_STAGES:
            if stage_name == "review":
                current_draft = await self.generate_stage(
                    current_draft.draft_id, "review", codex=codex
                )
                break

            current_stage = current_draft.stages.get(stage_name)
            if current_stage and current_stage.status == "valid":
                continue

            current_draft = await self.generate_stage(
                current_draft.draft_id, stage_name, codex=codex
            )
            stage_result = current_draft.stages.get(stage_name)
            if stage_result and stage_result.status != "valid":
                # Halt pipeline if a stage fails
                break

        return current_draft
