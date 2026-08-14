"""Combat encounter resolution (Victory, Defeat, Loot/XP, Soft Consequences)."""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.combat_state import CombatState, ParticipantSide
from domain.models.common import DisplayString, EntityId
from domain.models.enemy import EnemyArchetype, LootEntry
from domain.models.player_state import PlayerState
from domain.models.runtime_common import InventoryEntry
from domain.models.runtime_state import EncounterSummary
from domain.models.world_state import LocationState
from engine.combat.consequences import AuthoredConsequence, apply_player_consequences
from engine.combat.turns import is_side_defeated
from engine.dice.ports import RandomSource


@dataclass(frozen=True)
class VictoryRewards:
    """Rewards gained from a combat victory."""

    xp_gained: int
    items_dropped: list[InventoryEntry]
    world_flags: dict[EntityId, bool | int | str] = field(default_factory=dict)


@dataclass(frozen=True)
class DefeatOutcome:
    """Outcome of a combat defeat."""

    consequence: AuthoredConsequence
    is_game_over: bool = False


@dataclass(frozen=True)
class CombatResolutionResult:
    """Result of evaluating encounter termination."""

    is_resolved: bool
    outcome: str | None = None  # "Victory" or "Defeat"
    summary: EncounterSummary | None = None
    player: PlayerState = field(default_factory=lambda: None)  # type: ignore[assignment]
    location: LocationState = field(default_factory=lambda: None)  # type: ignore[assignment]
    world_flags: dict[EntityId, bool | int | str] = field(default_factory=dict)
    encounter_history: list[EncounterSummary] = field(default_factory=list)
    combat: CombatState | None = None
    rewards: VictoryRewards | None = None
    defeat_outcome: DefeatOutcome | None = None
    logs: list[str] = field(default_factory=list)


def add_item_to_inventory(
    inventory: list[InventoryEntry],
    item_id: EntityId,
    quantity: int,
) -> list[InventoryEntry]:
    """Add a quantity of an item to inventory, combining stack if possible."""
    if quantity <= 0:
        return list(inventory)

    new_inventory = list(inventory)
    idx = next(
        (
            i
            for i, entry in enumerate(new_inventory)
            if entry.item_id == item_id and entry.instance_data is None
        ),
        None,
    )
    if idx is not None:
        new_inventory[idx] = InventoryEntry(
            item_id=item_id,
            quantity=new_inventory[idx].quantity + quantity,
        )
    else:
        new_inventory.append(InventoryEntry(item_id=item_id, quantity=quantity))

    return new_inventory


def calculate_loot_drops(
    loot_table: list[LootEntry],
    rng: RandomSource | None = None,
) -> list[InventoryEntry]:
    """Calculate deterministic loot drops from a loot table.

    If min == max, no RNG is consumed.
    If min < max and rng is provided, rolls quantity within [min, max].
    """
    drops: list[InventoryEntry] = []
    for entry in loot_table:
        if entry.minimum_quantity == entry.maximum_quantity:
            qty = entry.minimum_quantity
        elif rng is not None:
            span = entry.maximum_quantity - entry.minimum_quantity + 1
            roll_val = rng.roll(100)
            qty = entry.minimum_quantity + (roll_val % span)
        else:
            qty = entry.minimum_quantity

        if qty > 0:
            drops.append(InventoryEntry(item_id=entry.item_id, quantity=qty))

    return drops


def resolve_combat_if_terminal(
    combat: CombatState,
    player: PlayerState,
    location: LocationState,
    world_flags: dict[EntityId, bool | int | str],
    encounter_history: list[EncounterSummary],
    enemy_archetypes: dict[EntityId, EnemyArchetype],
    authored_consequence: AuthoredConsequence | None = None,
    victory_flags: dict[EntityId, bool | int | str] | None = None,
    is_endgame_encounter: bool = False,
    rng: RandomSource | None = None,
) -> CombatResolutionResult:
    """Evaluate if combat has ended in Victory or Defeat and apply deterministic state updates.

    Idempotent: if not terminal, returns unmutated state with is_resolved=False.
    """
    # 1. Check Victory (all enemies defeated)
    if is_side_defeated(combat, ParticipantSide.ENEMY):
        logs: list[str] = ["Victory! All enemies have been defeated."]
        total_xp = 0
        all_drops: list[InventoryEntry] = []
        updated_inventory = list(player.inventory)

        # Collect XP and loot from enemy participants
        for pid, participant in combat.participants.items():
            if participant.side != ParticipantSide.ENEMY:
                continue

            # Look up enemy archetype by id prefix or entity id
            archetype = enemy_archetypes.get(pid)
            if archetype is None:
                # Fallback: check if pid matches archetype id prefix
                for arch_id, arch in enemy_archetypes.items():
                    if pid.startswith(arch_id):
                        archetype = arch
                        break

            if archetype is not None:
                total_xp += archetype.power_rating
                drops = calculate_loot_drops(archetype.loot_table, rng=rng)
                for drop in drops:
                    all_drops.append(drop)
                    updated_inventory = add_item_to_inventory(
                        updated_inventory, drop.item_id, drop.quantity
                    )
                    logs.append(f"Obtained loot: {drop.quantity}x {drop.item_id}.")

        new_player = player.model_copy(
            update={"xp": player.xp + total_xp, "inventory": updated_inventory}
        )
        logs.append(f"Gained {total_xp} XP (Total XP: {new_player.xp}).")

        new_flags = dict(world_flags)
        if victory_flags:
            for flag_id, val in victory_flags.items():
                new_flags[flag_id] = val
                logs.append(f"World flag '{flag_id}' set to {val}.")

        summary = EncounterSummary(
            encounter_id=combat.encounter_id,
            outcome=DisplayString("Victory"),
            round_count=combat.round,
        )
        new_history = [*encounter_history, summary]

        rewards = VictoryRewards(
            xp_gained=total_xp,
            items_dropped=all_drops,
            world_flags=victory_flags or {},
        )

        return CombatResolutionResult(
            is_resolved=True,
            outcome="Victory",
            summary=summary,
            player=new_player,
            location=location,
            world_flags=new_flags,
            encounter_history=new_history,
            combat=None,
            rewards=rewards,
            logs=logs,
        )

    # 2. Check Defeat (all party members defeated)
    if is_side_defeated(combat, ParticipantSide.PARTY):
        logs = ["Defeat! The party has fallen in battle."]

        if authored_consequence is None:
            raise ValueError("No authored consequence provided for protagonist defeat.")

        if authored_consequence.kind == "game_over" and not is_endgame_encounter:
            raise ValueError(
                "True game-over is forbidden in non-endgame encounters. "
                "Must use a soft defeat consequence."
            )

        new_player, new_location, new_flags, cons_logs = apply_player_consequences(
            player=player,
            location=location,
            world_flags=world_flags,
            consequence=authored_consequence,
        )
        logs.extend(cons_logs)

        # Soft defeat recovery: ensure protagonist has at least 1 HP upon recovery
        if new_player.hp.current <= 0 and authored_consequence.kind != "game_over":
            new_player = new_player.model_copy(
                update={"hp": new_player.hp.model_copy(update={"current": 1})}
            )

        summary = EncounterSummary(
            encounter_id=combat.encounter_id,
            outcome=DisplayString("Defeat"),
            round_count=combat.round,
        )
        new_history = [*encounter_history, summary]

        defeat_outcome = DefeatOutcome(
            consequence=authored_consequence,
            is_game_over=is_endgame_encounter and authored_consequence.kind == "game_over",
        )

        return CombatResolutionResult(
            is_resolved=True,
            outcome="Defeat",
            summary=summary,
            player=new_player,
            location=new_location,
            world_flags=new_flags,
            encounter_history=new_history,
            combat=None,
            defeat_outcome=defeat_outcome,
            logs=logs,
        )

    # 3. Not terminal
    return CombatResolutionResult(
        is_resolved=False,
        player=player,
        location=location,
        world_flags=world_flags,
        encounter_history=encounter_history,
        combat=combat,
        logs=[],
    )
