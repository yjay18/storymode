from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.routes.campaigns import _resolve_campaign_dir
from api.schemas.saves import CreateSaveRequest, SaveSummaryResponse
from app.config import Settings
from app.dependencies import get_settings
from campaign.storage.save_reader import SaveReader
from campaign.storage.save_writer import SaveWriter
from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import StatName
from domain.models.common import EntityId
from engine.campaign import load_campaign
from engine.state.creation import SaveCreationUseCase
from engine.state.errors import SaveError

router = APIRouter(prefix="/saves", tags=["saves"])


@router.post("", response_model=SaveSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_save(
    request: CreateSaveRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SaveSummaryResponse:
    """Create a new save with character creation."""
    # 1. Resolve campaign
    c_dir = _resolve_campaign_dir(settings, request.campaign_id)
    pack, _ = load_campaign(c_dir)
    if pack is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Campaign '{request.campaign_id}' is invalid or cannot be loaded",
        )

    save_id = f"save-{request.command_id}"
    root_dir = Path(settings.campaigns_dir).resolve()

    # 2. Check idempotency
    reader = SaveReader(root_dir)
    try:
        existing = reader.load_save(request.campaign_id, save_id)
        if existing.state and existing.meta:
            return SaveSummaryResponse(
                save_id=existing.state.save_id,
                campaign_id=existing.state.campaign_id,
                revision=existing.state.revision,
                player_name=existing.state.player.name,
                difficulty=existing.state.difficulty,
                current_area_id=existing.state.location.area_id,
                slot_name=existing.meta.slot_name,
                slot_kind=existing.meta.slot_kind,
            )
    except Exception:
        pass

    try:
        difficulty_enum = DefaultDifficulty(request.difficulty)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid difficulty '{request.difficulty}'",
        ) from None

    stat_dict: dict[StatName, int] = {}
    for k, v in request.stats.items():
        try:
            stat_dict[StatName(k)] = v
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid stat name '{k}'",
            ) from None

    # 3. Create save via use case
    use_case = SaveCreationUseCase()
    result = use_case.create_save(
        campaign_pack=pack,
        slot_kind=request.slot_kind,
        slot_name=request.slot_name,
        player_name=request.player_name,
        background_id=request.background_id,
        stats=stat_dict,
        difficulty=difficulty_enum,
        command_id=request.command_id,
        save_id=save_id,
    )

    if not result.success or result.state is None or result.meta is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.error_message or "Save creation failed",
        )

    # 4. Atomic persist
    writer = SaveWriter(root_dir)
    try:
        writer.write_state(result.state, result.meta, None)
    except SaveError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist save: {e}",
        ) from e

    return SaveSummaryResponse(
        save_id=result.state.save_id,
        campaign_id=result.state.campaign_id,
        revision=result.state.revision,
        player_name=result.state.player.name,
        difficulty=result.state.difficulty,
        current_area_id=result.state.location.area_id,
        slot_name=result.meta.slot_name,
        slot_kind=result.meta.slot_kind,
    )


@router.get("/{campaign_id}/{save_id}", response_model=SaveSummaryResponse)
def get_save(
    campaign_id: EntityId,
    save_id: EntityId,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SaveSummaryResponse:
    """Get save metadata and status."""
    root_dir = Path(settings.campaigns_dir).resolve()
    reader = SaveReader(root_dir)
    try:
        result = reader.load_save(campaign_id, save_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Save not found"
        ) from None

    meta = result.meta
    slot_name = meta.slot_name if meta else "Default"
    slot_kind = meta.slot_kind if meta else "manual"

    return SaveSummaryResponse(
        save_id=result.state.save_id,
        campaign_id=result.state.campaign_id,
        revision=result.state.revision,
        player_name=result.state.player.name,
        difficulty=result.state.difficulty,
        current_area_id=result.state.location.area_id,
        slot_name=slot_name,
        slot_kind=slot_kind,
    )
