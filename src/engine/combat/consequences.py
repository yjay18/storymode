"""Authored combat consequence application."""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.common import DisplayString, EntityId
from domain.models.player_state import PlayerState
from domain.models.runtime_common import ResourceValue
from domain.models.world_state import LocationState


@dataclass(frozen=True)
class AuthoredConsequence:
    """A deterministic, authored consequence for combat defeat, yield, or flee."""

    consequence_id: EntityId
    kind: str  # e.g. "capture", "relocation", "injury", "resource_loss", "world_flag"
    description: DisplayString
    relocation_area_id: EntityId | None = None
    hp_loss: int = 0
    mana_loss: int = 0
    world_flags: dict[EntityId, bool | int | str] = field(default_factory=dict)


def apply_player_consequences(
    player: PlayerState,
    location: LocationState,
    world_flags: dict[EntityId, bool | int | str],
    consequence: AuthoredConsequence,
) -> tuple[PlayerState, LocationState, dict[EntityId, bool | int | str], list[str]]:
    """Apply authored consequence updates to player, location, and world flags.

    Enforces deterministic bounds: HP cannot drop below 1 from soft consequences,
    mana cannot drop below 0.
    """
    logs: list[str] = [str(consequence.description)]
    new_player = player
    new_location = location
    new_flags = dict(world_flags)

    # HP / Mana loss
    if consequence.hp_loss > 0:
        new_hp_current = max(1, player.hp.current - consequence.hp_loss)
        new_player = new_player.model_copy(
            update={"hp": ResourceValue(current=new_hp_current, maximum=player.hp.maximum)}
        )
        logs.append(f"Lost {consequence.hp_loss} HP ({new_hp_current}/{player.hp.maximum}).")

    if consequence.mana_loss > 0:
        new_mana_current = max(0, player.mana.current - consequence.mana_loss)
        new_player = new_player.model_copy(
            update={"mana": ResourceValue(current=new_mana_current, maximum=player.mana.maximum)}
        )
        logs.append(
            f"Lost {consequence.mana_loss} mana ({new_mana_current}/{player.mana.maximum})."
        )

    # Relocation
    if consequence.relocation_area_id is not None:
        new_discovered = set(location.discovered_area_ids)
        new_discovered.add(consequence.relocation_area_id)
        new_location = LocationState(
            area_id=consequence.relocation_area_id,
            zone_anchor=None,
            discovered_area_ids=new_discovered,
        )
        logs.append(f"Relocated to area '{consequence.relocation_area_id}'.")

    # World flag updates
    for flag_id, val in consequence.world_flags.items():
        new_flags[flag_id] = val
        logs.append(f"World flag '{flag_id}' set to {val}.")

    return new_player, new_location, new_flags, logs
