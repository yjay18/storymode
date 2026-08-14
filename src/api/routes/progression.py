"""Progression and skills API endpoints (PROG-05)."""

import hashlib
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.routes.campaigns import _resolve_campaign_dir
from api.schemas.progression import (
    GrantXpRequest,
    InventoryItemView,
    KnownSkillView,
    PerformFusionRequest,
    PlayerProgressionView,
    ProgressionMutationResponse,
    ProgressionReceiptView,
    ProgressionViewResponse,
    SetLoadoutRequest,
    UpgradeSkillRequest,
)
from app.config import Settings
from app.dependencies import get_settings
from campaign.storage.save_reader import SaveReader
from campaign.storage.save_writer import SaveWriter
from domain.models.common import EntityId
from domain.models.pack import CampaignPack
from domain.models.runtime_state import RuntimeState
from domain.models.save_meta import SaveMeta
from engine.campaign import load_campaign
from engine.progression.use_cases import ProgressionUseCases
from engine.state.errors import IdempotentCommandError, StaleRevisionError

router = APIRouter(prefix="/saves/{campaign_id}/{save_id}/progression", tags=["progression"])


def _load_campaign_and_save(
    settings: Settings,
    campaign_id: EntityId,
    save_id: EntityId,
) -> tuple[CampaignPack, RuntimeState, SaveMeta, Path]:
    c_dir = _resolve_campaign_dir(settings, campaign_id)
    pack, _ = load_campaign(c_dir)
    if pack is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign '{campaign_id}' is invalid or cannot be loaded",
        )

    root_dir = Path(settings.campaigns_dir).resolve()
    reader = SaveReader(root_dir)
    try:
        load_result = reader.load_save(campaign_id, save_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Save '{save_id}' not found",
        ) from None

    if load_result.meta is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Save metadata missing",
        )

    return pack, load_result.state, load_result.meta, root_dir


def _build_progression_view(state: RuntimeState) -> PlayerProgressionView:
    p = state.player
    known = [
        KnownSkillView(skill_id=k.skill_id, current_level=k.level) for k in p.known_combat_skills
    ]
    inv = [InventoryItemView(item_id=i.item_id, quantity=i.quantity) for i in p.inventory]
    return PlayerProgressionView(
        id=p.id,
        name=p.name,
        level=p.level,
        xp=p.xp,
        upgrade_tokens=p.upgrade_tokens,
        hp_current=p.hp.current,
        hp_maximum=p.hp.maximum,
        mana_current=p.mana.current,
        mana_maximum=p.mana.maximum,
        combat_loadout=p.combat_loadout,
        known_skills=known,
        inventory=inv,
    )


@router.get("", response_model=ProgressionViewResponse)
def get_progression(
    campaign_id: EntityId,
    save_id: EntityId,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProgressionViewResponse:
    """Get player progression status, skills, and loadout."""
    _, state, _, _ = _load_campaign_and_save(settings, campaign_id, save_id)
    return ProgressionViewResponse(
        save_id=state.save_id,
        revision=state.revision,
        player=_build_progression_view(state),
    )


@router.post("/xp", response_model=ProgressionMutationResponse)
def grant_xp(
    campaign_id: EntityId,
    save_id: EntityId,
    request: GrantXpRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProgressionMutationResponse:
    """Grant XP to the protagonist and apply leveling."""
    pack, state, meta, root_dir = _load_campaign_and_save(settings, campaign_id, save_id)
    use_cases = ProgressionUseCases(pack)
    req_hash = hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()

    try:
        new_state, receipt = use_cases.grant_player_xp(
            state=state,
            expected_revision=request.expected_revision,
            command_id=request.command_id,
            request_hash=req_hash,
            xp_amount=request.xp_amount,
        )
    except (StaleRevisionError, IdempotentCommandError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    writer = SaveWriter(root_dir)
    writer.write_state(new_state, meta, None)

    return ProgressionMutationResponse(
        save_id=new_state.save_id,
        revision=new_state.revision,
        receipt=ProgressionReceiptView(
            command_id=receipt.command_id,
            committed_revision=receipt.committed_revision,
            result_kind=receipt.result_kind,
            safe_result_summary=receipt.safe_result_summary,
        ),
        player=_build_progression_view(new_state),
    )


@router.post("/upgrade", response_model=ProgressionMutationResponse)
def upgrade_skill(
    campaign_id: EntityId,
    save_id: EntityId,
    request: UpgradeSkillRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProgressionMutationResponse:
    """Upgrade a known combat skill consuming 1 upgrade token."""
    pack, state, meta, root_dir = _load_campaign_and_save(settings, campaign_id, save_id)
    use_cases = ProgressionUseCases(pack)
    req_hash = hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()

    try:
        new_state, receipt = use_cases.upgrade_combat_skill(
            state=state,
            expected_revision=request.expected_revision,
            command_id=request.command_id,
            request_hash=req_hash,
            skill_id=request.skill_id,
            target_id=request.target_id,
        )
    except (StaleRevisionError, IdempotentCommandError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    writer = SaveWriter(root_dir)
    writer.write_state(new_state, meta, None)

    return ProgressionMutationResponse(
        save_id=new_state.save_id,
        revision=new_state.revision,
        receipt=ProgressionReceiptView(
            command_id=receipt.command_id,
            committed_revision=receipt.committed_revision,
            result_kind=receipt.result_kind,
            safe_result_summary=receipt.safe_result_summary,
        ),
        player=_build_progression_view(new_state),
    )


@router.post("/loadout", response_model=ProgressionMutationResponse)
def set_loadout(
    campaign_id: EntityId,
    save_id: EntityId,
    request: SetLoadoutRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProgressionMutationResponse:
    """Update 4-slot combat loadout."""
    pack, state, meta, root_dir = _load_campaign_and_save(settings, campaign_id, save_id)
    use_cases = ProgressionUseCases(pack)
    req_hash = hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()

    try:
        new_state, receipt = use_cases.set_combat_loadout(
            state=state,
            expected_revision=request.expected_revision,
            command_id=request.command_id,
            request_hash=req_hash,
            loadout=request.loadout,
            target_id=request.target_id,
        )
    except (StaleRevisionError, IdempotentCommandError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    writer = SaveWriter(root_dir)
    writer.write_state(new_state, meta, None)

    return ProgressionMutationResponse(
        save_id=new_state.save_id,
        revision=new_state.revision,
        receipt=ProgressionReceiptView(
            command_id=receipt.command_id,
            committed_revision=receipt.committed_revision,
            result_kind=receipt.result_kind,
            safe_result_summary=receipt.safe_result_summary,
        ),
        player=_build_progression_view(new_state),
    )


@router.post("/fusion", response_model=ProgressionMutationResponse)
def perform_fusion(
    campaign_id: EntityId,
    save_id: EntityId,
    request: PerformFusionRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProgressionMutationResponse:
    """Execute a skill fusion transaction."""
    pack, state, meta, root_dir = _load_campaign_and_save(settings, campaign_id, save_id)
    use_cases = ProgressionUseCases(pack)
    req_hash = hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()

    try:
        new_state, receipt = use_cases.perform_skill_fusion(
            state=state,
            expected_revision=request.expected_revision,
            command_id=request.command_id,
            request_hash=req_hash,
            recipe_id=request.recipe_id,
            companion_id=request.companion_id,
        )
    except (StaleRevisionError, IdempotentCommandError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    writer = SaveWriter(root_dir)
    writer.write_state(new_state, meta, None)

    return ProgressionMutationResponse(
        save_id=new_state.save_id,
        revision=new_state.revision,
        receipt=ProgressionReceiptView(
            command_id=receipt.command_id,
            committed_revision=receipt.committed_revision,
            result_kind=receipt.result_kind,
            safe_result_summary=receipt.safe_result_summary,
        ),
        player=_build_progression_view(new_state),
    )
