"""Combat encounter initialization and participant snapshotting."""

from __future__ import annotations

from domain.models.area import EncounterEntry
from domain.models.audit import RollRecord
from domain.models.campaign_meta import DefaultDifficulty
from domain.models.character import CompanionDefinition
from domain.models.combat_state import CombatParticipant, CombatPhase, CombatState, ParticipantSide
from domain.models.common import EntityId
from domain.models.enemy import EnemyArchetype
from domain.models.party_state import LifeState
from domain.models.runtime_common import KnownCombatSkill, ResourceValue
from domain.models.runtime_state import RuntimeState
from domain.rules.difficulty import scale_enemy_hp
from engine.combat.turn_order import ParticipantInitiative, calculate_turn_order
from engine.dice.ports import RandomSource
from engine.dice.service import DiceService


def start_combat_encounter(
    state: RuntimeState,
    encounter: EncounterEntry,
    enemies_by_id: dict[EntityId, EnemyArchetype],
    companions_by_id: dict[EntityId, CompanionDefinition] | None = None,
    difficulty: DefaultDifficulty = DefaultDifficulty.NORMAL,
    rng: RandomSource | None = None,
    transaction_id: EntityId | None = None,
    command_id: EntityId | None = None,
    dice_service: DiceService | None = None,
) -> tuple[CombatState, list[RollRecord]]:
    """Initialize a new combat encounter snapshot from runtime state and definitions.

    Validates:
    - No existing active combat.
    - Protagonist is alive and not defeated.
    - Living present party members (protagonist + active alive companions <= 4).
    - Enemy archetypes exist and are scaled by difficulty profile.
    - Turn order calculated deterministically with audited tie-breaks.
    """
    if state.combat is not None:
        raise ValueError("Combat is already active")

    # Validate protagonist
    if state.player.hp.current <= 0:
        raise ValueError("Protagonist has 0 HP and cannot enter combat")

    # Validate party size and companion availability
    active_companions = state.party.active_companion_ids
    if len(active_companions) > 3:
        raise ValueError("Active companions cannot exceed 3 (max party size 4)")

    participants: dict[EntityId, CombatParticipant] = {}
    initiatives: list[ParticipantInitiative] = []

    # 1. Add protagonist
    player_id = state.player.id
    player_participant = CombatParticipant(
        hp=state.player.hp,
        armour=state.player.armour,
        mana=state.player.mana,
        statuses=list(state.player.statuses),
        known_combat_skills=list(state.player.known_combat_skills),
        combat_loadout=list(state.player.combat_loadout),
        faction_id=None,
        side=ParticipantSide.PARTY,
    )
    participants[player_id] = player_participant
    initiatives.append(
        ParticipantInitiative(
            participant_id=player_id,
            speed=state.player.speed,
            dexterity=state.player.stats.dexterity,
        )
    )

    # 2. Add living active companions
    companions_map = companions_by_id or {}
    for comp_id in active_companions:
        if comp_id not in state.party.companions:
            raise ValueError(f"Active companion {comp_id} not found in party runtime state")

        comp_state = state.party.companions[comp_id]
        if not comp_state.is_available or comp_state.life_state != LifeState.ALIVE:
            continue
        if comp_state.hp.current <= 0:
            continue

        comp_def = companions_map.get(comp_id)
        comp_dexterity = comp_def.base_stats.dexterity if comp_def else 10
        comp_faction = comp_def.faction_id if comp_def else None

        comp_participant = CombatParticipant(
            hp=comp_state.hp,
            armour=comp_state.armour,
            mana=comp_state.mana,
            statuses=[],
            known_combat_skills=list(comp_state.known_combat_skills),
            combat_loadout=list(comp_state.combat_loadout),
            faction_id=comp_faction,
            side=ParticipantSide.PARTY,
        )
        participants[comp_id] = comp_participant
        initiatives.append(
            ParticipantInitiative(
                participant_id=comp_id,
                speed=0,
                dexterity=comp_dexterity,
            )
        )

    # 3. Add enemies from encounter definition
    if not encounter.enemy_archetype_ids:
        raise ValueError("Encounter must contain at least one enemy archetype")

    archetype_counts: dict[EntityId, int] = {}
    for arch_id in encounter.enemy_archetype_ids:
        if arch_id not in enemies_by_id:
            raise ValueError(f"Enemy archetype {arch_id} not found in campaign enemies")
        archetype_counts[arch_id] = archetype_counts.get(arch_id, 0) + 1

    seen_counts: dict[EntityId, int] = {}
    for arch_id in encounter.enemy_archetype_ids:
        arch = enemies_by_id[arch_id]
        if archetype_counts[arch_id] > 1:
            idx = seen_counts.get(arch_id, 0) + 1
            seen_counts[arch_id] = idx
            instance_id = EntityId(f"{arch_id}_{idx}")
        else:
            instance_id = arch_id

        if instance_id in participants:
            raise ValueError(f"Duplicate combat participant ID: {instance_id}")

        scaled_hp_max = scale_enemy_hp(arch.base_hp, difficulty)
        enemy_hp = ResourceValue(current=scaled_hp_max, maximum=scaled_hp_max)
        enemy_armour = ResourceValue(current=arch.base_armour, maximum=arch.base_armour)
        enemy_mana = ResourceValue(current=arch.base_mana, maximum=arch.base_mana)

        known_skills = [
            KnownCombatSkill(skill_id=s, level=1, acquisition_source_id=s)
            for s in arch.combat_skill_ids
        ]

        enemy_participant = CombatParticipant(
            hp=enemy_hp,
            armour=enemy_armour,
            mana=enemy_mana,
            statuses=[],
            known_combat_skills=known_skills,
            combat_loadout=list(arch.combat_skill_ids),
            faction_id=arch.faction_id,
            side=ParticipantSide.ENEMY,
        )
        participants[instance_id] = enemy_participant
        initiatives.append(
            ParticipantInitiative(
                participant_id=instance_id,
                speed=arch.speed,
                dexterity=arch.dexterity,
            )
        )

    # 4. Calculate turn order
    order_result = calculate_turn_order(
        initiatives,
        rng=rng,
        dice_service=dice_service,
        transaction_id=transaction_id,
        revision=state.revision + 1,
        command_id=command_id,
    )

    combat_state = CombatState(
        encounter_id=encounter.id,
        phase=CombatPhase.ACTIVE,
        round=1,
        order=order_result.order,
        current_index=0,
        participants=participants,
        tie_break_records=order_result.tie_break_records,
        escape_policy=encounter.escape_policy_id,
        yield_policy=None,
    )

    return combat_state, order_result.roll_records
