"""Progression and party command use cases (PROG-05)."""

from __future__ import annotations

from domain.models.common import DisplayString, EntityId
from domain.models.pack import CampaignPack
from domain.models.runtime_state import CommandReceipt, RuntimeState
from engine.progression.companion_builds import build_companion_runtime
from engine.progression.fusion import execute_companion_fusion, execute_player_fusion
from engine.progression.leveling import grant_xp
from engine.progression.party import activate, deactivate, leave, recruit
from engine.progression.skills import (
    set_loadout,
    upgrade_skill,
)
from engine.state.transition import apply_command


class ProgressionUseCases:
    """Use cases for managing party membership, leveling, skills, and fusions."""

    def __init__(self, pack: CampaignPack) -> None:
        self.pack = pack
        self.skills_by_id = {s.id: s for s in pack.skills.combat_skills}
        self.recipes_by_id = {r.id: r for r in pack.skills.fusion_recipes}
        self.companions_by_id = {c.id: c for c in pack.characters.companions}

    def recruit_companion(
        self,
        state: RuntimeState,
        expected_revision: int,
        command_id: EntityId,
        request_hash: str,
        companion_id: EntityId,
    ) -> tuple[RuntimeState, CommandReceipt]:
        """Recruit an authored companion into the party."""
        if companion_id not in self.companions_by_id:
            raise ValueError(f"Companion {companion_id} not found in campaign pack")

        comp_def = self.companions_by_id[companion_id]

        def mutation(current_state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
            comp_runtime, errs = build_companion_runtime(comp_def, self.skills_by_id)
            if errs or comp_runtime is None:
                raise ValueError(f"Failed to build companion runtime: {errs}")

            updated_state = recruit(current_state, companion_id, comp_runtime)
            receipt = CommandReceipt(
                command_id=command_id,
                canonical_request_hash=request_hash,
                committed_revision=0,
                result_kind=DisplayString("recruit_companion"),
                safe_result_summary=DisplayString(f"Recruited companion {companion_id}"),
            )
            return updated_state, receipt

        return apply_command(
            state=state,
            expected_revision=expected_revision,
            command_id=command_id,
            canonical_request_hash=request_hash,
            mutation_fn=mutation,
        )

    def activate_companion(
        self,
        state: RuntimeState,
        expected_revision: int,
        command_id: EntityId,
        request_hash: str,
        companion_id: EntityId,
    ) -> tuple[RuntimeState, CommandReceipt]:
        """Activate a recruited companion in the active party roster."""

        def mutation(current_state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
            updated_state = activate(current_state, companion_id)
            receipt = CommandReceipt(
                command_id=command_id,
                canonical_request_hash=request_hash,
                committed_revision=0,
                result_kind=DisplayString("activate_companion"),
                safe_result_summary=DisplayString(f"Activated companion {companion_id}"),
            )
            return updated_state, receipt

        return apply_command(
            state=state,
            expected_revision=expected_revision,
            command_id=command_id,
            canonical_request_hash=request_hash,
            mutation_fn=mutation,
        )

    def deactivate_companion(
        self,
        state: RuntimeState,
        expected_revision: int,
        command_id: EntityId,
        request_hash: str,
        companion_id: EntityId,
    ) -> tuple[RuntimeState, CommandReceipt]:
        """Deactivate a companion from active party roster."""

        def mutation(current_state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
            updated_state = deactivate(current_state, companion_id)
            receipt = CommandReceipt(
                command_id=command_id,
                canonical_request_hash=request_hash,
                committed_revision=0,
                result_kind=DisplayString("deactivate_companion"),
                safe_result_summary=DisplayString(f"Deactivated companion {companion_id}"),
            )
            return updated_state, receipt

        return apply_command(
            state=state,
            expected_revision=expected_revision,
            command_id=command_id,
            canonical_request_hash=request_hash,
            mutation_fn=mutation,
        )

    def companion_leave(
        self,
        state: RuntimeState,
        expected_revision: int,
        command_id: EntityId,
        request_hash: str,
        companion_id: EntityId,
    ) -> tuple[RuntimeState, CommandReceipt]:
        """Remove a companion from party."""

        def mutation(current_state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
            updated_state = leave(current_state, companion_id)
            receipt = CommandReceipt(
                command_id=command_id,
                canonical_request_hash=request_hash,
                committed_revision=0,
                result_kind=DisplayString("companion_leave"),
                safe_result_summary=DisplayString(f"Companion {companion_id} left party"),
            )
            return updated_state, receipt

        return apply_command(
            state=state,
            expected_revision=expected_revision,
            command_id=command_id,
            canonical_request_hash=request_hash,
            mutation_fn=mutation,
        )

    def grant_player_xp(
        self,
        state: RuntimeState,
        expected_revision: int,
        command_id: EntityId,
        request_hash: str,
        xp_amount: int,
    ) -> tuple[RuntimeState, CommandReceipt]:
        """Grant XP to protagonist and apply level thresholds."""

        def mutation(current_state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
            updated_state, res = grant_xp(
                current_state, xp_amount, self.pack.balance.level_xp_thresholds
            )
            receipt = CommandReceipt(
                command_id=command_id,
                canonical_request_hash=request_hash,
                committed_revision=0,
                result_kind=DisplayString("grant_xp"),
                safe_result_summary=DisplayString(
                    f"Gained {xp_amount} XP, now level {res.new_level}"
                ),
            )
            return updated_state, receipt

        return apply_command(
            state=state,
            expected_revision=expected_revision,
            command_id=command_id,
            canonical_request_hash=request_hash,
            mutation_fn=mutation,
        )

    def upgrade_combat_skill(
        self,
        state: RuntimeState,
        expected_revision: int,
        command_id: EntityId,
        request_hash: str,
        skill_id: EntityId,
        target_id: EntityId | None = None,
    ) -> tuple[RuntimeState, CommandReceipt]:
        """Upgrade a combat skill by 1 level consuming 1 upgrade token."""

        def mutation(current_state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
            updated_state, res = upgrade_skill(
                current_state, skill_id, self.skills_by_id, target_id=target_id
            )
            receipt = CommandReceipt(
                command_id=command_id,
                canonical_request_hash=request_hash,
                committed_revision=0,
                result_kind=DisplayString("upgrade_skill"),
                safe_result_summary=DisplayString(
                    f"Upgraded skill {skill_id} to level {res.new_level}"
                ),
            )
            return updated_state, receipt

        return apply_command(
            state=state,
            expected_revision=expected_revision,
            command_id=command_id,
            canonical_request_hash=request_hash,
            mutation_fn=mutation,
        )

    def set_combat_loadout(
        self,
        state: RuntimeState,
        expected_revision: int,
        command_id: EntityId,
        request_hash: str,
        loadout: list[EntityId],
        target_id: EntityId | None = None,
    ) -> tuple[RuntimeState, CommandReceipt]:
        """Set the 4-slot combat loadout for a character outside combat."""

        def mutation(current_state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
            updated_state, res = set_loadout(current_state, loadout, target_id=target_id)
            receipt = CommandReceipt(
                command_id=command_id,
                canonical_request_hash=request_hash,
                committed_revision=0,
                result_kind=DisplayString("set_loadout"),
                safe_result_summary=DisplayString(
                    f"Updated combat loadout with {len(res.new_loadout)} skills"
                ),
            )
            return updated_state, receipt

        return apply_command(
            state=state,
            expected_revision=expected_revision,
            command_id=command_id,
            canonical_request_hash=request_hash,
            mutation_fn=mutation,
        )

    def perform_skill_fusion(
        self,
        state: RuntimeState,
        expected_revision: int,
        command_id: EntityId,
        request_hash: str,
        recipe_id: EntityId,
        companion_id: EntityId | None = None,
    ) -> tuple[RuntimeState, CommandReceipt]:
        """Perform a skill fusion transaction for protagonist or companion."""
        if recipe_id not in self.recipes_by_id:
            raise ValueError(f"Fusion recipe {recipe_id} not found in campaign")

        recipe = self.recipes_by_id[recipe_id]

        def mutation(current_state: RuntimeState) -> tuple[RuntimeState, CommandReceipt]:
            if companion_id is not None:
                if companion_id not in self.companions_by_id:
                    raise ValueError(f"Companion {companion_id} not found in campaign")
                comp_def = self.companions_by_id[companion_id]
                updated_state, c_res = execute_companion_fusion(
                    current_state,
                    companion_id,
                    recipe,
                    comp_def,
                    self.skills_by_id,
                )
                res_skill = c_res.result_skill_id
            else:
                updated_state, p_res = execute_player_fusion(
                    current_state, recipe, self.skills_by_id
                )
                res_skill = p_res.result_skill_id

            receipt = CommandReceipt(
                command_id=command_id,
                canonical_request_hash=request_hash,
                committed_revision=0,
                result_kind=DisplayString("fusion"),
                safe_result_summary=DisplayString(f"Successfully fused into skill {res_skill}"),
            )
            return updated_state, receipt

        return apply_command(
            state=state,
            expected_revision=expected_revision,
            command_id=command_id,
            canonical_request_hash=request_hash,
            mutation_fn=mutation,
        )
