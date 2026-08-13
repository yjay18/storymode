"""Combat effect bands."""

from enum import Enum


class CombatEffectBand(str, Enum):
    """Outcome bands for a combat effect die."""
    
    NATURAL_1 = "natural_1"
    LOW = "low"
    STANDARD = "standard"
    STRONG = "strong"
    NATURAL_20 = "natural_20"


def calculate_combat_band(roll: int) -> CombatEffectBand:
    """Calculate the outcome band for a combat effect die."""
    if roll == 20:
        return CombatEffectBand.NATURAL_20
    if roll == 1:
        return CombatEffectBand.NATURAL_1
    if 2 <= roll <= 9:
        return CombatEffectBand.LOW
    if 10 <= roll <= 14:
        return CombatEffectBand.STANDARD
    if 15 <= roll <= 19:
        return CombatEffectBand.STRONG
        
    raise ValueError(f"Roll {roll} out of bounds for d20 combat band")
