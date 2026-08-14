"""Party API endpoints (PROG-05)."""

import hashlib
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.routes.campaigns import _resolve_campaign_dir
from api.schemas.party import (
    ActivateCompanionRequest,
    CompanionView,
    DeactivateCompanionRequest,
    LeaveCompanionRequest,
    PartyMutationResponse,
    PartyReceiptView,
    PartyViewResponse,
    RecruitCompanionRequest,
)
from app.config import Settings
from app.dependencies import get_settings
from campaign.storage.save_reader import SaveReader
from campaign.storage.save_writer import SaveWriter
from domain.models.common import DisplayString, EntityId
from domain.models.pack import CampaignPack
from domain.models.runtime_state import RuntimeState
from domain.models.save_meta import SaveMeta
from engine.campaign import load_campaign
from engine.progression.use_cases import ProgressionUseCases
from engine.state.errors import IdempotentCommandError, StaleRevisionError

router = APIRouter(prefix="/saves/{campaign_id}/{save_id}/party", tags=["party"])


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


def _build_party_view(state: RuntimeState, pack: CampaignPack) -> PartyViewResponse:
    comp_defs = {c.id: c for c in pack.characters.companions}
    comps: list[CompanionView] = []
    for c in state.party.companions.values():
        c_def = comp_defs.get(c.id)
        comps.append(
            CompanionView(
                id=c.id,
                name=c_def.name if c_def else DisplayString(c.id),
                role=c_def.role if c_def else DisplayString("Companion"),
                life_state=c.life_state.value
                if hasattr(c.life_state, "value")
                else str(c.life_state),
                is_available=c.is_available,
                is_active=c.id in state.party.active_companion_ids,
                hp_current=c.hp.current,
                hp_maximum=c.hp.maximum,
                mana_current=c.mana.current,
                mana_maximum=c.mana.maximum,
                combat_loadout=c.combat_loadout,
                known_skill_ids=[k.skill_id for k in c.known_combat_skills],
            )
        )
    return PartyViewResponse(
        protagonist_id=state.party.protagonist_id,
        active_companion_ids=state.party.active_companion_ids,
        companions=comps,
    )


@router.get("", response_model=PartyViewResponse)
def get_party(
    campaign_id: EntityId,
    save_id: EntityId,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PartyViewResponse:
    """Get the current party roster and companions."""
    pack, state, _, _ = _load_campaign_and_save(settings, campaign_id, save_id)
    return _build_party_view(state, pack)


@router.post("/recruit", response_model=PartyMutationResponse)
def recruit_companion(
    campaign_id: EntityId,
    save_id: EntityId,
    request: RecruitCompanionRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PartyMutationResponse:
    """Recruit a companion into the party."""
    pack, state, meta, root_dir = _load_campaign_and_save(settings, campaign_id, save_id)
    use_cases = ProgressionUseCases(pack)
    req_hash = hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()

    try:
        new_state, receipt = use_cases.recruit_companion(
            state=state,
            expected_revision=request.expected_revision,
            command_id=request.command_id,
            request_hash=req_hash,
            companion_id=request.companion_id,
        )
    except StaleRevisionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except IdempotentCommandError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    writer = SaveWriter(root_dir)
    writer.write_state(new_state, meta, None)

    return PartyMutationResponse(
        save_id=new_state.save_id,
        revision=new_state.revision,
        receipt=PartyReceiptView(
            command_id=receipt.command_id,
            committed_revision=receipt.committed_revision,
            result_kind=receipt.result_kind,
            safe_result_summary=receipt.safe_result_summary,
        ),
        party=_build_party_view(new_state, pack),
    )


@router.post("/activate", response_model=PartyMutationResponse)
def activate_companion(
    campaign_id: EntityId,
    save_id: EntityId,
    request: ActivateCompanionRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PartyMutationResponse:
    """Activate a recruited companion."""
    pack, state, meta, root_dir = _load_campaign_and_save(settings, campaign_id, save_id)
    use_cases = ProgressionUseCases(pack)
    req_hash = hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()

    try:
        new_state, receipt = use_cases.activate_companion(
            state=state,
            expected_revision=request.expected_revision,
            command_id=request.command_id,
            request_hash=req_hash,
            companion_id=request.companion_id,
        )
    except (StaleRevisionError, IdempotentCommandError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    writer = SaveWriter(root_dir)
    writer.write_state(new_state, meta, None)

    return PartyMutationResponse(
        save_id=new_state.save_id,
        revision=new_state.revision,
        receipt=PartyReceiptView(
            command_id=receipt.command_id,
            committed_revision=receipt.committed_revision,
            result_kind=receipt.result_kind,
            safe_result_summary=receipt.safe_result_summary,
        ),
        party=_build_party_view(new_state, pack),
    )


@router.post("/deactivate", response_model=PartyMutationResponse)
def deactivate_companion(
    campaign_id: EntityId,
    save_id: EntityId,
    request: DeactivateCompanionRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PartyMutationResponse:
    """Deactivate an active companion."""
    pack, state, meta, root_dir = _load_campaign_and_save(settings, campaign_id, save_id)
    use_cases = ProgressionUseCases(pack)
    req_hash = hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()

    try:
        new_state, receipt = use_cases.deactivate_companion(
            state=state,
            expected_revision=request.expected_revision,
            command_id=request.command_id,
            request_hash=req_hash,
            companion_id=request.companion_id,
        )
    except (StaleRevisionError, IdempotentCommandError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    writer = SaveWriter(root_dir)
    writer.write_state(new_state, meta, None)

    return PartyMutationResponse(
        save_id=new_state.save_id,
        revision=new_state.revision,
        receipt=PartyReceiptView(
            command_id=receipt.command_id,
            committed_revision=receipt.committed_revision,
            result_kind=receipt.result_kind,
            safe_result_summary=receipt.safe_result_summary,
        ),
        party=_build_party_view(new_state, pack),
    )


@router.post("/leave", response_model=PartyMutationResponse)
def companion_leave(
    campaign_id: EntityId,
    save_id: EntityId,
    request: LeaveCompanionRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PartyMutationResponse:
    """Remove a companion from party."""
    pack, state, meta, root_dir = _load_campaign_and_save(settings, campaign_id, save_id)
    use_cases = ProgressionUseCases(pack)
    req_hash = hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()

    try:
        new_state, receipt = use_cases.companion_leave(
            state=state,
            expected_revision=request.expected_revision,
            command_id=request.command_id,
            request_hash=req_hash,
            companion_id=request.companion_id,
        )
    except (StaleRevisionError, IdempotentCommandError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    writer = SaveWriter(root_dir)
    writer.write_state(new_state, meta, None)

    return PartyMutationResponse(
        save_id=new_state.save_id,
        revision=new_state.revision,
        receipt=PartyReceiptView(
            command_id=receipt.command_id,
            committed_revision=receipt.committed_revision,
            result_kind=receipt.result_kind,
            safe_result_summary=receipt.safe_result_summary,
        ),
        party=_build_party_view(new_state, pack),
    )
