"""Combat resource manipulation and damage routing rules."""

from __future__ import annotations

from dataclasses import dataclass

from domain.models.runtime_common import ResourceValue


@dataclass(frozen=True)
class DamageResult:
    """Detailed audit of an applied damage instance."""

    damage: int
    armour_before: int
    armour_absorbed: int
    armour_after: int
    hp_before: int
    hp_damage: int
    hp_after: int
    is_defeated: bool


def apply_damage(
    hp: ResourceValue, armour: ResourceValue, damage: int
) -> tuple[ResourceValue, ResourceValue, DamageResult]:
    """Route damage through armour first, then HP.

    Absorbs damage up to current armour, subtracting the remainder from HP.
    Clamps HP at zero and returns updated ResourceValues and DamageResult.
    Raises TypeError if damage is a bool or not an int.
    Raises ValueError if damage is negative.
    """
    if isinstance(damage, bool):
        raise TypeError("Boolean value not allowed for damage")
    if not isinstance(damage, int):
        raise TypeError("Damage must be an integer")
    if damage < 0:
        raise ValueError(f"Damage must be non-negative, got {damage}")

    armour_before = armour.current
    absorbed = min(armour_before, damage)
    armour_after = armour_before - absorbed
    remaining_damage = damage - absorbed

    hp_before = hp.current
    hp_damage = min(hp_before, remaining_damage)
    hp_after = max(0, hp_before - remaining_damage)

    new_armour = ResourceValue(current=armour_after, maximum=armour.maximum)
    new_hp = ResourceValue(current=hp_after, maximum=hp.maximum)

    result = DamageResult(
        damage=damage,
        armour_before=armour_before,
        armour_absorbed=absorbed,
        armour_after=armour_after,
        hp_before=hp_before,
        hp_damage=hp_damage,
        hp_after=hp_after,
        is_defeated=(hp_after == 0),
    )

    return new_hp, new_armour, result


def apply_healing(hp: ResourceValue, amount: int) -> tuple[ResourceValue, int]:
    """Apply healing up to maximum HP.

    Returns the new ResourceValue and the actual amount healed.
    Raises TypeError if amount is a bool or not an int.
    Raises ValueError if amount is negative.
    """
    if isinstance(amount, bool):
        raise TypeError("Boolean value not allowed for healing amount")
    if not isinstance(amount, int):
        raise TypeError("Healing amount must be an integer")
    if amount < 0:
        raise ValueError(f"Healing amount must be non-negative, got {amount}")

    healed = min(amount, hp.maximum - hp.current)
    new_hp = ResourceValue(current=hp.current + healed, maximum=hp.maximum)
    return new_hp, healed


def apply_mana_delta(mana: ResourceValue, delta: int) -> tuple[ResourceValue, int]:
    """Apply a positive or negative mana change.

    If negative, checks for sufficient mana.
    If positive, caps at maximum mana.
    Returns the new ResourceValue and the actual change applied.
    """
    if isinstance(delta, bool):
        raise TypeError("Boolean value not allowed for mana delta")
    if not isinstance(delta, int):
        raise TypeError("Mana delta must be an integer")

    if delta < 0:
        cost = -delta
        if cost > mana.current:
            raise ValueError(f"Insufficient mana: required {cost}, current {mana.current}")
        new_mana = ResourceValue(current=mana.current - cost, maximum=mana.maximum)
        return new_mana, delta

    gained = min(delta, mana.maximum - mana.current)
    new_mana = ResourceValue(current=mana.current + gained, maximum=mana.maximum)
    return new_mana, gained
