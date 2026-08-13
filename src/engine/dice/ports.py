"""Ports for dependency injection in the dice engine."""

from typing import Protocol


class RandomSource(Protocol):
    """Protocol for generating random numbers."""

    def roll(self, sides: int) -> int:
        """Roll a die with the given number of sides (inclusive 1..sides).
        
        Args:
            sides: The number of sides on the die. Must be >= 2.
            
        Returns:
            An integer between 1 and sides, inclusive.
            
        Raises:
            ValueError: If sides is less than 2.
        """
        ...
