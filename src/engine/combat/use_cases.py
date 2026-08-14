"""Combat use cases orchestrator (start, skill, defend, flee, yield, AI turns)."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from domain.models.area import EncounterEntry
from domain.models.character import CompanionDefinition
from domain.models.combat_state import CombatPhase, CombatState, ParticipantSide
from domain.models.common import DisplayString, EntityId
from domain.models.enemy import EnemyArchetype
from domain.models.runtime_state import CommandReceipt, EncounterSummary, RuntimeState
from domain.models.skill import CombatSkill
from engine.combat.commands import AllowedCombatAction, get_allowed_combat_actions
from engine.combat.consequences import AuthoredConsequence, apply_player_consequences
from engine.combat.defend import execute_defend_command
from engine.combat.encounter import start_combat_encounter
from engine.combat.escape import (
    EscapePolicyDefinition,
    YieldPolicyDefinition,
    execute_flee_command,
    execute_yield_command,
)
from engine.combat.resolution import resolve_combat_if_terminal
from engine.combat.skills import execute_skill_command
from engine.combat.turns import advance_turn, process_turn_start
from engine.dice.ports import RandomSource
from engine.dice.service import DiceService

if TYPE_CHECKING:
    from domain.models.campaign_meta import DefaultDifficulty


@dataclasses.dataclass(frozen=True)
class CombatExecutionResult:
    """Outcome of executing a combat command."""

    state: RuntimeState
    logs: list[str]
    allowed_actions: list[AllowedCombatAction] = dataclasses.field(default_factory=list)
    is_terminal: bool = False
    outcome: str | None = None  # "Victory", "Defeat", "Escaped", "Yielded"


class CombatUseCases:
    """Orchestrates deterministic combat flow, state transitions, and AI turn processing."""

    def __init__(
        self,
        skills: dict[EntityId, CombatSkill],
        enemy_archetypes: dict[EntityId, EnemyArchetype],
        dice_service: DiceService,
        rng: RandomSource | None = None,
        companions: dict[EntityId, CompanionDefinition] | None = None,
        escape_policies: dict[EntityId, EscapePolicyDefinition] | None = None,
        yield_policies: dict[EntityId, YieldPolicyDefinition] | None = None,
        defeat_consequences: dict[EntityId, AuthoredConsequence] | None = None,
    ) -> None:
        self._skills = skills
        self._enemy_archetypes = enemy_archetypes
        self._dice_service = dice_service
        self._rng = rng
        self._companions = companions or {}
        self._escape_policies = escape_policies or {}
        self._yield_policies = yield_policies or {}
        self._defeat_consequences = defeat_consequences or {}

    def _check_idempotency(
        self,
        state: RuntimeState,
        command_id: EntityId,
    ) -> RuntimeState | None:
        for receipt in state.last_command_receipts:
            if receipt.command_id == command_id:
                return state
        return None

    def _validate_revision(self, state: RuntimeState, expected_revision: int) -> None:
        if state.revision != expected_revision:
            msg = (
                f"State revision conflict: expected {expected_revision}, "
                f"current is {state.revision}"
            )
            raise ValueError(msg)

    def _get_active_escape_policy(self, combat: CombatState) -> EscapePolicyDefinition | None:
        if combat.encounter_id in self._escape_policies:
            return self._escape_policies[combat.encounter_id]
        from engine.dice.checks import ExplorationBand

        return EscapePolicyDefinition(
            id=EntityId("default_escape"),
            dc=10,
            consequences={
                ExplorationBand.SUCCESS: AuthoredConsequence(
                    consequence_id=EntityId("flee_strong"),
                    kind="flee",
                    description=DisplayString("You escaped safely."),
                ),
                ExplorationBand.PARTIAL_SUCCESS: AuthoredConsequence(
                    consequence_id=EntityId("flee_weak"),
                    kind="flee",
                    description=DisplayString("You escaped but took a hit."),
                    hp_loss=2,
                ),
                ExplorationBand.FAILURE: AuthoredConsequence(
                    consequence_id=EntityId("flee_miss"),
                    kind="flee",
                    description=DisplayString("You failed to escape."),
                    hp_loss=4,
                ),
            },
            ends_combat_on_success=True,
            ends_combat_on_partial=True,
        )

    def _get_active_yield_policy(self, combat: CombatState) -> YieldPolicyDefinition | None:
        if combat.encounter_id in self._yield_policies:
            return self._yield_policies[combat.encounter_id]
        return YieldPolicyDefinition(
            id=EntityId("default_yield"),
            allowed=True,
            consequence=AuthoredConsequence(
                consequence_id=EntityId("yield_cons"),
                kind="yield",
                description=DisplayString("You yielded to your foes."),
            ),
        )

    def _get_active_defeat_consequence(self, combat: CombatState) -> AuthoredConsequence | None:
        if combat.encounter_id in self._defeat_consequences:
            return self._defeat_consequences[combat.encounter_id]
        return AuthoredConsequence(
            consequence_id=EntityId("default_defeat"),
            kind="defeat",
            description=DisplayString("You were defeated in battle."),
        )

    def get_allowed_actions(self, state: RuntimeState) -> list[AllowedCombatAction]:
        """Compute all valid combat actions for the current active actor."""
        if state.combat is None or state.combat.phase != CombatPhase.ACTIVE:
            return []

        active_actor_id = state.combat.order[state.combat.current_index]
        return get_allowed_combat_actions(
            combat=state.combat,
            actor_id=active_actor_id,
            skills_by_id=self._skills,
        )

    def start_combat(
        self,
        state: RuntimeState,
        encounter_id: EntityId,
        enemy_archetype_ids: list[EntityId],
        command_id: EntityId,
        expected_revision: int,
        difficulty: DefaultDifficulty | None = None,
        escape_policy_id: EntityId | None = None,
    ) -> CombatExecutionResult:
        """Initialize an encounter into active CombatState."""
        if idempotent_state := self._check_idempotency(state, command_id):
            return CombatExecutionResult(
                state=idempotent_state,
                logs=["Idempotent combat start returned existing state."],
                allowed_actions=self.get_allowed_actions(idempotent_state),
            )

        self._validate_revision(state, expected_revision)

        if state.combat is not None and state.combat.phase == CombatPhase.ACTIVE:
            raise ValueError("Cannot start combat: another combat encounter is already active.")

        active_difficulty = difficulty or state.difficulty
        encounter_entry = EncounterEntry(
            id=encounter_id,
            enemy_archetype_ids=enemy_archetype_ids,
            condition=DisplayString("always"),
            weight=100,
            escape_policy_id=escape_policy_id or encounter_id,
            consequence_ids=[],
        )

        combat_state, rolls = start_combat_encounter(
            state=state,
            encounter=encounter_entry,
            enemies_by_id=self._enemy_archetypes,
            companions_by_id=self._companions,
            difficulty=active_difficulty,
            rng=self._rng,
            dice_service=self._dice_service,
        )

        # Process round 1 turn 1 start status & mana for the first actor
        mana_map: dict[EntityId, int] = {state.player.id: state.player.mana_regen}
        first_actor = combat_state.order[combat_state.current_index]
        combat_state, _can_act, start_logs = process_turn_start(
            combat=combat_state,
            actor_id=first_actor,
            mana_regen=mana_map.get(first_actor, 0),
        )
        init_logs = [
            f"Encounter '{encounter_id}' started with {len(combat_state.order)} combatants."
        ]
        all_logs = [*init_logs, *start_logs]

        receipt = CommandReceipt(
            command_id=command_id,
            canonical_request_hash="",
            committed_revision=state.revision + 1,
            result_kind=DisplayString("combat"),
            safe_result_summary=DisplayString(f"Started combat encounter '{encounter_id}'."),
            roll_ids=[r.roll_id for r in rolls],
        )

        new_state = state.model_copy(
            update={
                "combat": combat_state,
                "revision": state.revision + 1,
                "last_command_receipts": [*state.last_command_receipts[-9:], receipt],
            }
        )

        # Run AI turns if first actor is enemy
        return self._run_ai_turns_if_needed(new_state, all_logs)

    def execute_skill(
        self,
        state: RuntimeState,
        skill_id: EntityId,
        target_ids: list[EntityId],
        command_id: EntityId,
        expected_revision: int,
    ) -> CombatExecutionResult:
        """Execute a player combat skill and process turn advancement / AI turns."""
        if idempotent_state := self._check_idempotency(state, command_id):
            return CombatExecutionResult(
                state=idempotent_state,
                logs=["Idempotent skill execution returned existing state."],
                allowed_actions=self.get_allowed_actions(idempotent_state),
            )

        self._validate_revision(state, expected_revision)

        if state.combat is None or state.combat.phase != CombatPhase.ACTIVE:
            raise ValueError("No active combat encounter.")

        active_actor_id = state.combat.order[state.combat.current_index]
        participant = state.combat.participants.get(active_actor_id)
        if participant is None or participant.side != ParticipantSide.PARTY:
            raise ValueError(f"Actor '{active_actor_id}' is not an active party participant.")

        combat_res = execute_skill_command(
            combat=state.combat,
            actor_id=active_actor_id,
            skill_id=skill_id,
            target_ids=target_ids,
            skills_by_id=self._skills,
            dice_service=self._dice_service,
        )

        receipt = CommandReceipt(
            command_id=command_id,
            canonical_request_hash="",
            committed_revision=state.revision + 1,
            result_kind=DisplayString("combat"),
            safe_result_summary=DisplayString(f"Used skill '{skill_id}' on {target_ids}."),
            roll_ids=[r.roll_id for r in combat_res.roll_records],
        )

        new_state = state.model_copy(
            update={
                "combat": combat_res.combat_state,
                "revision": state.revision + 1,
                "last_command_receipts": [*state.last_command_receipts[-9:], receipt],
            }
        )

        # Check terminal state or advance turn
        return self._post_action_step(new_state, combat_res.logs)

    def execute_defend(
        self,
        state: RuntimeState,
        command_id: EntityId,
        expected_revision: int,
    ) -> CombatExecutionResult:
        """Execute Defend command (0-cost Guarded) and process turn advancement."""
        if idempotent_state := self._check_idempotency(state, command_id):
            return CombatExecutionResult(
                state=idempotent_state,
                logs=["Idempotent defend execution returned existing state."],
                allowed_actions=self.get_allowed_actions(idempotent_state),
            )

        self._validate_revision(state, expected_revision)

        if state.combat is None or state.combat.phase != CombatPhase.ACTIVE:
            raise ValueError("No active combat encounter.")

        active_actor_id = state.combat.order[state.combat.current_index]
        participant = state.combat.participants.get(active_actor_id)
        if participant is None or participant.side != ParticipantSide.PARTY:
            raise ValueError(f"Actor '{active_actor_id}' is not an active party participant.")

        defend_res = execute_defend_command(state.combat, active_actor_id)

        receipt = CommandReceipt(
            command_id=command_id,
            canonical_request_hash="",
            committed_revision=state.revision + 1,
            result_kind=DisplayString("combat"),
            safe_result_summary=DisplayString(f"Actor '{active_actor_id}' defended."),
        )

        new_state = state.model_copy(
            update={
                "combat": defend_res.combat_state,
                "revision": state.revision + 1,
                "last_command_receipts": [*state.last_command_receipts[-9:], receipt],
            }
        )

        return self._post_action_step(new_state, defend_res.logs)

    def execute_flee(
        self,
        state: RuntimeState,
        command_id: EntityId,
        expected_revision: int,
    ) -> CombatExecutionResult:
        """Execute Flee command against encounter escape policy."""
        if idempotent_state := self._check_idempotency(state, command_id):
            return CombatExecutionResult(
                state=idempotent_state,
                logs=["Idempotent flee execution returned existing state."],
                allowed_actions=self.get_allowed_actions(idempotent_state),
            )

        self._validate_revision(state, expected_revision)

        if state.combat is None or state.combat.phase != CombatPhase.ACTIVE:
            raise ValueError("No active combat encounter.")

        active_actor_id = state.combat.order[state.combat.current_index]
        escape_policy = self._get_active_escape_policy(state.combat)
        if escape_policy is None:
            raise ValueError("Fleeing is not available for this encounter.")

        flee_res = execute_flee_command(
            combat=state.combat,
            actor_id=active_actor_id,
            escape_policy=escape_policy,
            dice_service=self._dice_service,
            difficulty=state.difficulty,
        )

        all_logs = list(flee_res.logs)
        roll_ids = [flee_res.roll_record.roll_id] if flee_res.roll_record else []
        receipt = CommandReceipt(
            command_id=command_id,
            canonical_request_hash="",
            committed_revision=state.revision + 1,
            result_kind=DisplayString("combat"),
            safe_result_summary=DisplayString(f"Flee attempt: {flee_res.band.value}."),
            roll_ids=roll_ids,
        )

        if flee_res.combat_ended:
            new_player = state.player
            new_location = state.location
            new_flags = dict(state.world_flags)

            if flee_res.consequence_applied:
                new_player, new_location, new_flags, cons_logs = apply_player_consequences(
                    player=new_player,
                    location=new_location,
                    world_flags=new_flags,
                    consequence=flee_res.consequence_applied,
                )
                all_logs.extend(cons_logs)

            summary = EncounterSummary(
                encounter_id=state.combat.encounter_id,
                outcome=DisplayString("Escaped"),
                round_count=state.combat.round,
            )
            new_history = [*state.encounter_history, summary]

            new_state = state.model_copy(
                update={
                    "player": new_player,
                    "location": new_location,
                    "world_flags": new_flags,
                    "encounter_history": new_history,
                    "combat": None,
                    "revision": state.revision + 1,
                    "last_command_receipts": [*state.last_command_receipts[-9:], receipt],
                }
            )
            return CombatExecutionResult(
                state=new_state,
                logs=all_logs,
                is_terminal=True,
                outcome="Escaped",
            )

        # Flee failed: advance turn to next actor
        new_state = state.model_copy(
            update={
                "combat": flee_res.updated_combat,
                "revision": state.revision + 1,
                "last_command_receipts": [*state.last_command_receipts[-9:], receipt],
            }
        )
        return self._post_action_step(new_state, all_logs)

    def execute_yield(
        self,
        state: RuntimeState,
        command_id: EntityId,
        expected_revision: int,
    ) -> CombatExecutionResult:
        """Execute Yield command applying authored yield consequence."""
        if idempotent_state := self._check_idempotency(state, command_id):
            return CombatExecutionResult(
                state=idempotent_state,
                logs=["Idempotent yield execution returned existing state."],
                allowed_actions=self.get_allowed_actions(idempotent_state),
            )

        self._validate_revision(state, expected_revision)

        if state.combat is None or state.combat.phase != CombatPhase.ACTIVE:
            raise ValueError("No active combat encounter.")

        active_actor_id = state.combat.order[state.combat.current_index]
        yield_policy = self._get_active_yield_policy(state.combat)
        if yield_policy is None:
            raise ValueError("Yield policy not found for encounter.")

        yield_res = execute_yield_command(state.combat, active_actor_id, yield_policy)

        all_logs = list(yield_res.logs)
        new_player, new_location, new_flags, cons_logs = apply_player_consequences(
            player=state.player,
            location=state.location,
            world_flags=state.world_flags,
            consequence=yield_res.consequence_applied,
        )
        all_logs.extend(cons_logs)

        summary = EncounterSummary(
            encounter_id=state.combat.encounter_id,
            outcome=DisplayString("Yielded"),
            round_count=state.combat.round,
        )
        new_history = [*state.encounter_history, summary]

        receipt = CommandReceipt(
            command_id=command_id,
            canonical_request_hash="",
            committed_revision=state.revision + 1,
            result_kind=DisplayString("combat"),
            safe_result_summary=DisplayString(
                f"Yielded in encounter '{state.combat.encounter_id}'."
            ),
        )

        new_state = state.model_copy(
            update={
                "player": new_player,
                "location": new_location,
                "world_flags": new_flags,
                "encounter_history": new_history,
                "combat": None,
                "revision": state.revision + 1,
                "last_command_receipts": [*state.last_command_receipts[-9:], receipt],
            }
        )

        return CombatExecutionResult(
            state=new_state,
            logs=all_logs,
            is_terminal=True,
            outcome="Yielded",
        )

    def _post_action_step(
        self,
        state: RuntimeState,
        action_logs: list[str],
    ) -> CombatExecutionResult:
        """Resolve terminal status or advance turn and run AI turns."""
        if state.combat is None:
            return CombatExecutionResult(
                state=state,
                logs=action_logs,
                is_terminal=True,
            )

        # Check victory/defeat
        defeat_consequence = self._get_active_defeat_consequence(state.combat)
        res_check = resolve_combat_if_terminal(
            combat=state.combat,
            player=state.player,
            location=state.location,
            world_flags=state.world_flags,
            encounter_history=state.encounter_history,
            enemy_archetypes=self._enemy_archetypes,
            authored_consequence=defeat_consequence,
            rng=self._rng,
        )

        if res_check.is_resolved:
            new_state = state.model_copy(
                update={
                    "player": res_check.player,
                    "location": res_check.location,
                    "world_flags": res_check.world_flags,
                    "encounter_history": res_check.encounter_history,
                    "combat": None,
                }
            )
            return CombatExecutionResult(
                state=new_state,
                logs=[*action_logs, *res_check.logs],
                is_terminal=True,
                outcome=res_check.outcome,
            )

        # Advance to next participant turn
        mana_map: dict[EntityId, int] = {state.player.id: state.player.mana_regen}

        next_combat, _next_actor, _can_act, adv_logs = advance_turn(
            combat=state.combat,
            mana_regen_by_id=mana_map,
        )
        adv_state = state.model_copy(update={"combat": next_combat})
        combined_logs = [*action_logs, *adv_logs]

        return self._run_ai_turns_if_needed(adv_state, combined_logs)

    def _run_ai_turns_if_needed(
        self,
        state: RuntimeState,
        logs: list[str],
    ) -> CombatExecutionResult:
        """Run consecutive enemy AI turns until a player turn or battle ends."""
        current_state = state
        accumulated_logs = list(logs)

        while current_state.combat is not None and current_state.combat.phase == CombatPhase.ACTIVE:
            active_actor_id = current_state.combat.order[current_state.combat.current_index]
            participant = current_state.combat.participants.get(active_actor_id)

            if participant is None or participant.side != ParticipantSide.ENEMY:
                break  # Party actor turn reached

            # Enemy AI turn
            enemy_logs: list[str] = [f"--- Enemy turn: {active_actor_id} ---"]

            # Select skill
            archetype = self._enemy_archetypes.get(active_actor_id)
            if archetype is None:
                for arch_id, arch in self._enemy_archetypes.items():
                    if active_actor_id.startswith(arch_id):
                        archetype = arch
                        break

            chosen_skill: CombatSkill | None = None
            if archetype and archetype.combat_skill_ids:
                for s_id in archetype.combat_skill_ids:
                    sk = self._skills.get(s_id)
                    if sk and participant.mana.current >= sk.levels[0].mana_cost:
                        chosen_skill = sk
                        break

            # Find target (first living party participant)
            target_ids = [
                pid
                for pid, p in current_state.combat.participants.items()
                if p.side == ParticipantSide.PARTY and p.hp.current > 0
            ]

            if chosen_skill and target_ids:
                exec_res = execute_skill_command(
                    combat=current_state.combat,
                    actor_id=active_actor_id,
                    skill_id=chosen_skill.id,
                    target_ids=[target_ids[0]],
                    skills_by_id=self._skills,
                    dice_service=self._dice_service,
                )
                enemy_logs.extend(exec_res.logs)
                updated_combat = exec_res.combat_state
            else:
                enemy_logs.append(f"{active_actor_id} takes no action.")
                updated_combat = current_state.combat

            current_state = current_state.model_copy(update={"combat": updated_combat})
            accumulated_logs.extend(enemy_logs)

            # Check if party defeated or battle resolved
            defeat_consequence = self._get_active_defeat_consequence(updated_combat)
            res_check = resolve_combat_if_terminal(
                combat=updated_combat,
                player=current_state.player,
                location=current_state.location,
                world_flags=current_state.world_flags,
                encounter_history=current_state.encounter_history,
                enemy_archetypes=self._enemy_archetypes,
                authored_consequence=defeat_consequence,
                rng=self._rng,
            )

            if res_check.is_resolved:
                final_state = current_state.model_copy(
                    update={
                        "player": res_check.player,
                        "location": res_check.location,
                        "world_flags": res_check.world_flags,
                        "encounter_history": res_check.encounter_history,
                        "combat": None,
                    }
                )
                return CombatExecutionResult(
                    state=final_state,
                    logs=[*accumulated_logs, *res_check.logs],
                    is_terminal=True,
                    outcome=res_check.outcome,
                )

            # Advance to next turn
            if current_state.combat is None:
                break

            mana_map: dict[EntityId, int] = {
                current_state.player.id: current_state.player.mana_regen
            }
            next_combat, _next_actor, _can_act, adv_logs = advance_turn(
                combat=current_state.combat,
                mana_regen_by_id=mana_map,
            )
            current_state = current_state.model_copy(update={"combat": next_combat})
            accumulated_logs.extend(adv_logs)

        allowed = self.get_allowed_actions(current_state)
        return CombatExecutionResult(
            state=current_state,
            logs=accumulated_logs,
            allowed_actions=allowed,
            is_terminal=current_state.combat is None,
        )
