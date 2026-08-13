"""Secure random source for production."""

import secrets

from engine.dice.ports import RandomSource


class SecureRandomSource(RandomSource):
    """Production random source backed by OS secure randomness."""

    def __init__(self) -> None:
        self._rng = secrets.SystemRandom()

    def roll(self, sides: int) -> int:
        if sides < 2:
            raise ValueError(f"sides must be >= 2, got {sides}")
        return self._rng.randint(1, sides)
