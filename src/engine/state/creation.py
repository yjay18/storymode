"""Character and save creation use case."""

import datetime
from dataclasses import dataclass

from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import BackgroundDefinition, StatName
from domain.models.common import EntityId
from domain.models.pack import CampaignPack
from domain.models.party_state import PartyState
from domain.models.player_state import PlayerState
from domain.models.plot_state import PlotState
from domain.models.runtime_common import ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.models.save_meta import SaveMeta
from domain.models.world_state import LocationState
from domain.rules.point_buy import apply_background_bonus, validate_point_buy


@dataclass(frozen=True)
class CreationResult:
    """Result of creating a character/save."""

    success: bool
    state: RuntimeState | None = None
    meta: SaveMeta | None = None
    error_code: str | None = None
    error_message: str | None = None


class SaveCreationUseCase:
    """Orchestrates character creation and initial save persistence."""

    def create_save(
        self,
        campaign_pack: CampaignPack,
        slot_kind: str,
        slot_name: str,
        player_name: str,
        background_id: EntityId,
        stats: dict[StatName, int],
        difficulty: DefaultDifficulty,
        command_id: EntityId,
        save_id: EntityId | None = None,
        now: datetime.datetime | None = None,
    ) -> CreationResult:
        """Create a new initial save state for a campaign."""
        if now is None:
            now = datetime.datetime.now(datetime.UTC)

        if save_id is None:
            # Generate stable/unique save_id
            save_id = f"save-{command_id}"

        # 1. Validate background
        bg: BackgroundDefinition | None = None
        for b in campaign_pack.characters.protagonist_backgrounds:
            if b.id == background_id:
                bg = b
                break

        if bg is None:
            return CreationResult(
                success=False,
                error_code="invalid_background",
                error_message=f"Background '{background_id}' not found in campaign",
            )

        # 2. Validate point buy
        pb_res = validate_point_buy(stats, campaign_pack.skills.point_buy)
        if not pb_res.is_valid:
            return CreationResult(
                success=False,
                error_code="invalid_point_buy",
                error_message="; ".join(pb_res.errors),
            )

        # 3. Apply background bonus
        applied = apply_background_bonus(stats, bg, campaign_pack.skills.point_buy)
        if not applied.is_valid or applied.stats is None:
            return CreationResult(
                success=False,
                error_code="invalid_background_bonus",
                error_message="; ".join(applied.errors),
            )

        # 4. Starting area
        start_area_id = "area-start"
        start_area_name = "Starting Area"
        if campaign_pack.areas.areas:
            start_area_id = campaign_pack.areas.areas[0].id
            start_area_name = campaign_pack.areas.areas[0].name

        # 5. Build PlayerState
        from domain.models.runtime_common import KnownCombatSkill

        known_combat = [
            KnownCombatSkill(skill_id=s, level=1, acquisition_source_id=bg.id)
            for s in bg.starting_skill_ids
        ]
        player = PlayerState(
            id="player-1",
            name=player_name,
            background_id=background_id,
            stats=applied.stats,
            hp=ResourceValue(current=10, maximum=10),
            armour=ResourceValue(current=2, maximum=5),
            mana=ResourceValue(current=5, maximum=5),
            mana_regen=1,
            speed=30,
            luck_capacity=3,
            luck_current=2,
            inventory=[],
            equipment=[],
            known_combat_skills=known_combat,
            combat_loadout=list(bg.starting_skill_ids[:4]),
        )

        # 6. Build RuntimeState
        fingerprint = campaign_pack.meta.content_fingerprint or "draft"
        state = RuntimeState(
            campaign_id=campaign_pack.meta.campaign_id,
            campaign_version=str(campaign_pack.meta.campaign_version),
            campaign_fingerprint=fingerprint,
            save_id=save_id,
            revision=1,
            difficulty=difficulty,
            player=player,
            party=PartyState(protagonist_id="player-1"),
            location=LocationState(area_id=start_area_id),
            plot=PlotState(),
        )

        # 7. Build SaveMeta
        meta = SaveMeta(
            campaign_id=campaign_pack.meta.campaign_id,
            campaign_version=str(campaign_pack.meta.campaign_version),
            save_id=save_id,
            derived_from_revision=1,
            slot_kind=slot_kind,
            slot_name=slot_name,
            player_display_name=player_name,
            player_level=1,
            campaign_title=campaign_pack.meta.title,
            current_area_display_name=start_area_name,
            difficulty=difficulty,
            created_at=now,
            updated_at=now,
            recovery_status="ok",
        )

        return CreationResult(
            success=True,
            state=state,
            meta=meta,
        )
