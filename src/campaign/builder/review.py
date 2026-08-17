"""Campaign builder review, manual edits, and validation report service (BUILD-07).

Guarantees:
- Typed editing of individual owning draft artifacts with revision checking.
- Executes local schema validation then cross-file reference, graph, and balance validation.
- Produces sorted, structured diagnostics (errors vs warnings).
- Determines definitive publish-readiness predicate without mutating other artifacts.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from campaign.builder.models import (
    ALL_DRAFT_STAGES,
    DraftStage,
    DraftStageState,
    DraftState,
    StageDiagnostic,
    StageStatus,
)
from campaign.storage.drafts import DraftRepository
from domain.models.common import EntityId, FrozenModel
from domain.models.diagnostics import Diagnostic
from engine.validation.balance import validate_balance
from engine.validation.campaign_files import validate_campaign_files
from engine.validation.graphs import validate_graphs
from engine.validation.references import index_campaign_entities, validate_references
from llm.contracts.campaign_generation import (
    AreasStageResponse,
    CharactersStageResponse,
    MetaStyleStageResponse,
    PlotStageResponse,
    SkillsStageResponse,
    WorldStageResponse,
)

STAGE_CONTRACT_MAP: dict[DraftStage, type[BaseModel]] = {
    "meta_style": MetaStyleStageResponse,
    "rules": WorldStageResponse,
    "areas": AreasStageResponse,
    "plot": PlotStageResponse,
    "characters": CharactersStageResponse,
    "skills": SkillsStageResponse,
}


class ValidationReport(FrozenModel):
    """Structured report of campaign draft validation state."""

    draft_id: str
    is_valid: bool
    is_publish_ready: bool
    errors: list[StageDiagnostic]
    warnings: list[StageDiagnostic]


class DraftReviewService:
    """Provides typed artifact review edits and full campaign validation reports."""

    def __init__(self, draft_repo: DraftRepository) -> None:
        self.draft_repo = draft_repo

    def edit_stage_artifact(
        self,
        draft_id: EntityId | str,
        stage: DraftStage,
        artifact_data: dict[str, Any],
        expected_revision: int,
    ) -> tuple[DraftState, list[StageDiagnostic]]:
        """Edit a single stage artifact with optimistic concurrency and schema validation."""
        draft = self.draft_repo.load_draft(draft_id)

        contract_cls = STAGE_CONTRACT_MAP.get(stage)
        diagnostics: list[StageDiagnostic] = []
        stage_status: StageStatus

        if contract_cls is not None:
            try:
                # Validate typed replacement
                contract_cls.model_validate_json(json.dumps(artifact_data))
                stage_status = "valid"
            except (ValidationError, ValueError) as e:
                stage_status = "invalid"
                if isinstance(e, ValidationError):
                    for err in e.errors():
                        field_loc = "/".join(str(loc) for loc in err["loc"])
                        diagnostics.append(
                            StageDiagnostic(
                                stage=stage,
                                code="SCHEMA_VALIDATION_ERROR",
                                message=err["msg"],
                                field_path=field_loc,
                                is_error=True,
                            )
                        )
                else:
                    diagnostics.append(
                        StageDiagnostic(
                            stage=stage,
                            code="SCHEMA_VALIDATION_ERROR",
                            message=str(e),
                            is_error=True,
                        )
                    )
        else:
            stage_status = "valid"

        updated_stage = DraftStageState(
            stage=stage,
            status=stage_status,
            attempts=draft.stages.get(stage, DraftStageState(stage=stage)).attempts,
            diagnostics=diagnostics,
            artifact_data=artifact_data if stage_status == "valid" else None,
        )

        final_stages = dict(draft.stages)
        final_stages[stage] = updated_stage

        saved_draft = self.draft_repo.save_draft(
            draft.model_copy(update={"stages": final_stages, "diagnostics": diagnostics}),
            expected_revision=expected_revision,
        )
        return saved_draft, diagnostics

    def validate_draft(self, draft_id: EntityId | str) -> ValidationReport:
        """Run complete multi-stage and cross-file validation on a campaign draft."""
        draft = self.draft_repo.load_draft(draft_id)
        errors: list[StageDiagnostic] = []
        warnings: list[StageDiagnostic] = []

        # 1. Check stage completeness
        missing_stages = [
            st for st in ALL_DRAFT_STAGES if st != "review" and draft.stages.get(st) is None
        ]
        invalid_stages = [
            st
            for st in ALL_DRAFT_STAGES
            if st != "review" and draft.stages.get(st) and draft.stages[st].status != "valid"
        ]

        if missing_stages or invalid_stages:
            for st in missing_stages:
                errors.append(
                    StageDiagnostic(
                        stage=st,
                        code="MISSING_STAGE",
                        message=f"Stage '{st}' has not been generated.",
                        is_error=True,
                    )
                )
            for st in invalid_stages:
                st_state = draft.stages[st]
                if st_state.diagnostics:
                    errors.extend(st_state.diagnostics)
                else:
                    errors.append(
                        StageDiagnostic(
                            stage=st,
                            code=f"STAGE_{st_state.status.upper()}",
                            message=f"Stage '{st}' is {st_state.status}.",
                            is_error=True,
                        )
                    )
            return ValidationReport(
                draft_id=str(draft.draft_id),
                is_valid=False,
                is_publish_ready=False,
                errors=errors,
                warnings=warnings,
            )

        # 2. Extract JSON files from artifacts
        file_contents = self._assemble_draft_files(draft)
        if not file_contents:
            errors.append(
                StageDiagnostic(
                    stage="review",
                    code="EMPTY_ARTIFACTS",
                    message="No valid artifact data found in draft stages.",
                    is_error=True,
                )
            )
            return ValidationReport(
                draft_id=str(draft.draft_id),
                is_valid=False,
                is_publish_ready=False,
                errors=errors,
                warnings=warnings,
            )

        # 3. Parse campaign files
        pack, parse_diags = validate_campaign_files(file_contents)
        if pack is None:
            for d in parse_diags:
                errors.append(self._to_stage_diagnostic(d))
            return ValidationReport(
                draft_id=str(draft.draft_id),
                is_valid=False,
                is_publish_ready=False,
                errors=errors,
                warnings=warnings,
            )

        # 4. Cross-file references
        index, ref_diags = index_campaign_entities(pack)
        if ref_diags:
            for d in ref_diags:
                errors.append(self._to_stage_diagnostic(d))
            return ValidationReport(
                draft_id=str(draft.draft_id),
                is_valid=False,
                is_publish_ready=False,
                errors=errors,
                warnings=warnings,
            )

        for d in validate_references(pack, index):
            errors.append(self._to_stage_diagnostic(d))

        # 5. Graphs
        for d in validate_graphs(pack):
            errors.append(self._to_stage_diagnostic(d))

        # 6. Balance
        for d in validate_balance(pack):
            errors.append(self._to_stage_diagnostic(d))

        is_valid = len(errors) == 0
        return ValidationReport(
            draft_id=str(draft.draft_id),
            is_valid=is_valid,
            is_publish_ready=is_valid,
            errors=errors,
            warnings=warnings,
        )

    def _assemble_draft_files(self, draft: DraftState) -> dict[str, str]:
        """Convert stage artifact dictionaries into simulated campaign pack JSON files."""
        files: dict[str, str] = {}
        for stage_name, stage_state in draft.stages.items():
            if not stage_state.artifact_data:
                continue
            data = stage_state.artifact_data
            if stage_name == "meta_style":
                if "meta" in data:
                    files["campaign.json"] = json.dumps(data["meta"])
                if "style" in data:
                    files["style_bible.json"] = json.dumps(data["style"])
            elif stage_name == "rules":
                if "world" in data:
                    files["world.json"] = json.dumps(data["world"])
            elif stage_name == "areas":
                if "areas" in data:
                    files["areas.json"] = json.dumps(data["areas"])
            elif stage_name == "plot":
                if "plot" in data:
                    files["plot.json"] = json.dumps(data["plot"])
            elif stage_name == "characters":
                if "characters" in data:
                    files["characters.json"] = json.dumps(data["characters"])
            elif stage_name == "skills":
                if "skills" in data:
                    files["skills.json"] = json.dumps(data["skills"])
                if "items" in data:
                    files["items.json"] = json.dumps(data["items"])
                if "enemies" in data:
                    files["enemies.json"] = json.dumps(data["enemies"])
                if "balance" in data:
                    files["balance.json"] = json.dumps(data["balance"])
        return files

    def _to_stage_diagnostic(self, d: Diagnostic) -> StageDiagnostic:
        """Map engine Diagnostic to StageDiagnostic."""
        stage_map = {
            "campaign.json": "meta_style",
            "style_bible.json": "meta_style",
            "world.json": "rules",
            "areas.json": "areas",
            "plot.json": "plot",
            "characters.json": "characters",
            "skills.json": "skills",
            "items.json": "skills",
            "enemies.json": "skills",
            "balance.json": "skills",
        }
        target_stage: DraftStage = stage_map.get(d.file or "", "review")  # type: ignore[assignment]
        return StageDiagnostic(
            stage=target_stage,
            code=d.code,
            message=d.message,
            field_path=d.json_pointer,
            is_error=True,
        )
