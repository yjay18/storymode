"""Plot and opportunities API endpoints (PROG-05)."""

import hashlib
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.routes.campaigns import _resolve_campaign_dir
from api.schemas.plot import (
    ClockView,
    MilestoneView,
    OpportunityView,
    PlotMutationResponse,
    PlotReceiptView,
    PlotViewResponse,
    ResolveOpportunityRequest,
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
from engine.plot.opportunities import evaluate_opportunity_status
from engine.plot.use_cases import PlotUseCases
from engine.state.errors import IdempotentCommandError, StaleRevisionError

router = APIRouter(prefix="/saves/{campaign_id}/{save_id}/plot", tags=["plot"])


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


def _build_plot_view(state: RuntimeState, pack: CampaignPack) -> PlotViewResponse:
    milestones = [
        MilestoneView(
            id=m.id,
            status=state.plot.milestones.get(m.id, "locked"),
            is_current=m.id in state.plot.current_milestone_ids,
        )
        for m in pack.plot.milestones
    ]

    opportunities: list[OpportunityView] = []
    for opp_def in pack.plot.authored_opportunities:
        inst = state.plot.opportunities.get(opp_def.id)
        stat = evaluate_opportunity_status(opp_def, inst, state)
        opportunities.append(
            OpportunityView(
                id=opp_def.id,
                title=opp_def.title,
                description=opp_def.description,
                status=stat.value,
                parent_milestone_id=opp_def.parent_milestone_id,
                allowed_outcome_ids=opp_def.allowed_outcome_ids,
                is_resolved=inst.is_resolved if inst else False,
            )
        )

    clocks = [
        ClockView(
            id=c.clock_id,
            current=c.current,
            maximum=c.maximum,
            completed=c.completed,
        )
        for c in state.clocks.values()
    ]

    return PlotViewResponse(
        save_id=state.save_id,
        revision=state.revision,
        current_milestone_ids=list(state.plot.current_milestone_ids),
        milestones=milestones,
        opportunities=opportunities,
        clocks=clocks,
        ending_state=state.plot.ending_state,
    )


@router.get("", response_model=PlotViewResponse)
def get_plot(
    campaign_id: EntityId,
    save_id: EntityId,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PlotViewResponse:
    """Get the current plot overview, milestone statuses, opportunities, and clocks."""
    pack, state, _, _ = _load_campaign_and_save(settings, campaign_id, save_id)
    return _build_plot_view(state, pack)


@router.post("/opportunities/resolve", response_model=PlotMutationResponse)
def resolve_opportunity(
    campaign_id: EntityId,
    save_id: EntityId,
    request: ResolveOpportunityRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PlotMutationResponse:
    """Resolve an opportunity with an authorized outcome."""
    pack, state, meta, root_dir = _load_campaign_and_save(settings, campaign_id, save_id)
    use_cases = PlotUseCases(pack)
    req_hash = hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()

    try:
        new_state, receipt = use_cases.resolve_opportunity(
            state=state,
            expected_revision=request.expected_revision,
            command_id=request.command_id,
            request_hash=req_hash,
            opportunity_id=request.opportunity_id,
            outcome_id=request.outcome_id,
        )
    except (StaleRevisionError, IdempotentCommandError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    writer = SaveWriter(root_dir)
    writer.write_state(new_state, meta, None)

    return PlotMutationResponse(
        save_id=new_state.save_id,
        revision=new_state.revision,
        receipt=PlotReceiptView(
            command_id=receipt.command_id,
            committed_revision=receipt.committed_revision,
            result_kind=receipt.result_kind,
            safe_result_summary=receipt.safe_result_summary,
        ),
        plot=_build_plot_view(new_state, pack),
    )
