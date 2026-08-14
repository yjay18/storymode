"""Combat effect application and closed registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from domain.models.combat_state import CombatParticipant
from domain.models.common import EntityId
from domain.models.runtime_common import ResourceValue, StatusInstance
from domain.models.skill import EffectDefinition, EffectKind
from domain.rules.combat_resources import apply_damage, apply_healing, apply_mana_delta


@dataclass(frozen=True)
class EffectApplicationResult:
    """Detailed record of an applied combat effect."""

    effect_id: EntityId
    kind: EffectKind
    target_id: EntityId
    applied: bool
    details: dict[str, Any]
    log_message: str


def apply_effect(
    effect: EffectDefinition,
    target_id: EntityId,
    target: CombatParticipant,
    immunities: set[EntityId] | None = None,
) -> tuple[CombatParticipant, EffectApplicationResult]:
    """Apply an atomic effect to a combat participant.

    Routes damage armour-first, checks for Guarded damage reduction,
    respects explicit typed immunities, and applies healing/status/resource effects.
    """
    immunity_set = immunities or set()

    # Check immunity
    if effect.effect_id in immunity_set or (effect.status_id and effect.status_id in immunity_set):
        result = EffectApplicationResult(
            effect_id=effect.effect_id,
            kind=effect.kind,
            target_id=target_id,
            applied=False,
            details={"immune": True},
            log_message=f"{target_id} is immune to {effect.effect_id}.",
        )
        return target, result

    match effect.kind:
        case EffectKind.DAMAGE:
            incoming_damage = effect.magnitude

            # Check if target is Guarded (25% reduction, min 1 reduction, then consumed)
            guarded_idx = next(
                (i for i, s in enumerate(target.statuses) if s.status_id == EntityId("guarded")),
                None,
            )
            statuses = list(target.statuses)
            reduced_by = 0
            if guarded_idx is not None:
                reduced_by = max(1, incoming_damage * 25 // 100)
                incoming_damage = max(0, incoming_damage - reduced_by)
                statuses.pop(guarded_idx)

            new_hp, new_armour, dmg_res = apply_damage(target.hp, target.armour, incoming_damage)
            updated_target = target.model_copy(
                update={"hp": new_hp, "armour": new_armour, "statuses": statuses}
            )

            msg = (
                f"{target_id} took {incoming_damage} damage "
                f"({dmg_res.armour_absorbed} absorbed by armour, {dmg_res.hp_damage} to HP). "
                f"HP is now {new_hp.current}/{new_hp.maximum}."
            )
            if reduced_by > 0:
                msg = f"[Guarded -{reduced_by}] " + msg

            result = EffectApplicationResult(
                effect_id=effect.effect_id,
                kind=effect.kind,
                target_id=target_id,
                applied=True,
                details={
                    "original_damage": effect.magnitude,
                    "reduced_by_guard": reduced_by,
                    "final_damage": incoming_damage,
                    "armour_absorbed": dmg_res.armour_absorbed,
                    "hp_damage": dmg_res.hp_damage,
                    "hp_remaining": new_hp.current,
                    "is_defeated": dmg_res.is_defeated,
                },
                log_message=msg,
            )
            return updated_target, result

        case EffectKind.HEAL:
            new_hp, healed = apply_healing(target.hp, effect.magnitude)
            updated_target = target.model_copy(update={"hp": new_hp})
            result = EffectApplicationResult(
                effect_id=effect.effect_id,
                kind=effect.kind,
                target_id=target_id,
                applied=True,
                details={"healed": healed, "hp_current": new_hp.current},
                log_message=f"{target_id} healed {healed} HP ({new_hp.current}/{new_hp.maximum}).",
            )
            return updated_target, result

        case EffectKind.STATUS:
            if not effect.status_id:
                raise ValueError("STATUS effect must specify a status_id")

            statuses = list(target.statuses)
            # Check non-stacking refresh
            existing_idx = next(
                (i for i, s in enumerate(statuses) if s.status_id == effect.status_id),
                None,
            )
            if existing_idx is not None:
                # Refresh duration without stacking magnitude
                statuses[existing_idx] = StatusInstance(
                    status_id=effect.status_id,
                    duration_remaining=effect.duration,
                    magnitude=effect.magnitude,
                )
            else:
                statuses.append(
                    StatusInstance(
                        status_id=effect.status_id,
                        duration_remaining=effect.duration,
                        magnitude=effect.magnitude,
                    )
                )

            updated_target = target.model_copy(update={"statuses": statuses})
            result = EffectApplicationResult(
                effect_id=effect.effect_id,
                kind=effect.kind,
                target_id=target_id,
                applied=True,
                details={
                    "status_id": effect.status_id,
                    "duration": effect.duration,
                    "magnitude": effect.magnitude,
                },
                log_message=f"{target_id} gained status '{effect.status_id}'.",
            )
            return updated_target, result

        case EffectKind.RESOURCE_DRAIN:
            drain = min(target.mana.current, effect.magnitude)
            new_mana = ResourceValue(
                current=target.mana.current - drain, maximum=target.mana.maximum
            )
            updated_target = target.model_copy(update={"mana": new_mana})
            log_msg = f"{target_id} lost {drain} mana ({new_mana.current}/{new_mana.maximum})."
            result = EffectApplicationResult(
                effect_id=effect.effect_id,
                kind=effect.kind,
                target_id=target_id,
                applied=True,
                details={"mana_drained": drain},
                log_message=log_msg,
            )
            return updated_target, result

        case EffectKind.RESOURCE_RESTORE:
            new_mana, gained = apply_mana_delta(target.mana, effect.magnitude)
            updated_target = target.model_copy(update={"mana": new_mana})
            log_msg = f"{target_id} restored {gained} mana ({new_mana.current}/{new_mana.maximum})."
            result = EffectApplicationResult(
                effect_id=effect.effect_id,
                kind=effect.kind,
                target_id=target_id,
                applied=True,
                details={"mana_restored": gained},
                log_message=log_msg,
            )
            return updated_target, result

        case EffectKind.BUFF | EffectKind.DEBUFF:
            if effect.status_id:
                return apply_effect(
                    effect.model_copy(update={"kind": EffectKind.STATUS}),
                    target_id,
                    target,
                    immunities,
                )
            result = EffectApplicationResult(
                effect_id=effect.effect_id,
                kind=effect.kind,
                target_id=target_id,
                applied=True,
                details={"magnitude": effect.magnitude},
                log_message=f"{target_id} received {effect.kind} ({effect.magnitude}).",
            )
            return target, result
