"""FastAPI routes for campaign creation, generation, review, and publication (BUILD-09)."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from api.schemas.builder import (
    CreateGuidedDraftRequest,
    CreateQuickDraftRequest,
    EditStageRequest,
    GenerateStageRequest,
    PublishDraftRequest,
)
from campaign.builder.models import (
    DraftStage,
    DraftState,
)
from campaign.builder.normalization import (
    create_initial_draft_state,
    normalize_builder_brief,
    normalize_quick_prompt,
)
from campaign.builder.review import DraftReviewService, ValidationReport
from campaign.generation import GenerationOrchestrator, StageRunner
from campaign.storage.drafts import (
    DraftNotFoundError,
    DraftRepository,
    DraftRevisionConflictError,
)
from campaign.storage.publisher import (
    CampaignAlreadyExistsError,
    CampaignPublisher,
    InvalidDraftPublishError,
    PublishResult,
    UnconfirmedPublishError,
)
from domain.models.common import EntityId
from engine.state.errors import UnsafePathError
from llm.ollama_client import OllamaClient

router = APIRouter(prefix="/builder", tags=["builder"])


def _get_draft_repo(request: Request) -> DraftRepository:
    root_dir = Path(request.app.state.settings.campaigns_dir).parent
    return DraftRepository(root_dir)


def _get_review_service(request: Request) -> DraftReviewService:
    repo = _get_draft_repo(request)
    return DraftReviewService(repo)


def _get_orchestrator(request: Request) -> GenerationOrchestrator:
    repo = _get_draft_repo(request)
    client = OllamaClient(base_url=str(request.app.state.settings.ollama_url))
    runner = StageRunner(client, repo)
    return GenerationOrchestrator(runner, repo)


def _get_publisher(request: Request) -> CampaignPublisher:
    repo = _get_draft_repo(request)
    review_svc = _get_review_service(request)
    return CampaignPublisher(Path(request.app.state.settings.campaigns_dir), repo, review_svc)


@router.post("/drafts/guided", response_model=DraftState, status_code=201)
async def create_guided_draft(
    payload: CreateGuidedDraftRequest,
    request: Request,
) -> DraftState:
    """Create a new campaign draft from a guided builder brief."""
    repo = _get_draft_repo(request)
    draft_id = EntityId(f"draft-{uuid.uuid4().hex[:8]}")
    normalized_brief = normalize_builder_brief(payload.brief)
    draft = create_initial_draft_state(draft_id, normalized_brief)
    return repo.save_draft(draft)


@router.post("/drafts/quick", response_model=DraftState, status_code=201)
async def create_quick_draft(
    payload: CreateQuickDraftRequest,
    request: Request,
) -> DraftState:
    """Create a new campaign draft from a quick prompt input."""
    repo = _get_draft_repo(request)
    draft_id = EntityId(f"draft-{uuid.uuid4().hex[:8]}")
    brief = normalize_quick_prompt(payload.quick_input)
    draft = create_initial_draft_state(draft_id, brief)
    return repo.save_draft(draft)


@router.get("/drafts", response_model=list[DraftState])
async def list_drafts(request: Request) -> list[DraftState]:
    """List all persisted campaign drafts."""
    repo = _get_draft_repo(request)
    return repo.list_drafts()


@router.get("/drafts/{draft_id}", response_model=DraftState)
async def get_draft(draft_id: str, request: Request) -> DraftState:
    """Get the current state of a campaign draft."""
    repo = _get_draft_repo(request)
    try:
        return repo.load_draft(draft_id)
    except DraftNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UnsafePathError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/drafts/{draft_id}/generate", response_model=DraftState)
async def generate_draft(
    draft_id: str,
    payload: GenerateStageRequest,
    request: Request,
) -> DraftState:
    """Trigger generation for a specific stage or all ungenerated stages."""
    orchestrator = _get_orchestrator(request)
    try:
        if payload.stage is not None:
            return await orchestrator.generate_stage(draft_id, payload.stage)
        return await orchestrator.generate_all(draft_id)
    except DraftNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UnsafePathError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/drafts/{draft_id}/cancel", response_model=DraftState)
async def cancel_draft(draft_id: str, request: Request) -> DraftState:
    """Cancel in-progress or pending generation stages in a draft."""
    repo = _get_draft_repo(request)
    try:
        return repo.cancel_draft(draft_id)
    except DraftNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UnsafePathError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.put("/drafts/{draft_id}/stages/{stage}", response_model=DraftState)
async def edit_stage(
    draft_id: str,
    stage: DraftStage,
    payload: EditStageRequest,
    request: Request,
) -> DraftState:
    """Edit a single stage artifact with optimistic revision check."""
    review_svc = _get_review_service(request)
    try:
        updated_draft, _ = review_svc.edit_stage_artifact(
            draft_id=draft_id,
            stage=stage,
            artifact_data=payload.artifact_data,
            expected_revision=payload.expected_revision,
        )
        return updated_draft
    except DraftNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except DraftRevisionConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except UnsafePathError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/drafts/{draft_id}/validate", response_model=ValidationReport)
async def validate_draft(draft_id: str, request: Request) -> ValidationReport:
    """Run full validation across all draft stages and return a diagnostic report."""
    review_svc = _get_review_service(request)
    try:
        return review_svc.validate_draft(draft_id)
    except DraftNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UnsafePathError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/drafts/{draft_id}/publish", response_model=PublishResult)
async def publish_draft(
    draft_id: str,
    payload: PublishDraftRequest,
    request: Request,
) -> PublishResult:
    """Publish a validated draft atomically into an immutable campaign pack."""
    publisher = _get_publisher(request)
    try:
        return publisher.publish_draft(draft_id=draft_id, confirmed=payload.confirmed)
    except UnconfirmedPublishError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except InvalidDraftPublishError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except CampaignAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except DraftNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except UnsafePathError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
