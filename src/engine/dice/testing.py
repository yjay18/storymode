"""Scripted random source for testing."""

from engine.dice.ports import RandomSource


class ScriptedRandomSource(RandomSource):
    """A deterministic random source that returns pre-queued values."""

    def __init__(self, queued_rolls: list[int]) -> None:
        # We store them in reverse so we can pop() efficiently from the end
        self._queue = list(reversed(queued_rolls))
        self.call_count = 0

    def roll(self, sides: int) -> int:
        if sides < 2:
            raise ValueError(f"sides must be >= 2, got {sides}")
            
        if not self._queue:
            raise RuntimeError("ScriptedRandomSource exhausted its queued values")
            
        value = self._queue.pop()
        self.call_count += 1
        
        if not (1 <= value <= sides):
            raise ValueError(
                f"Queued value {value} is out of bounds for d{sides}"
            )
            
        return value

    def assert_exhausted(self) -> None:
        """Assert that all queued values have been consumed."""
        if self._queue:
            raise AssertionError(f"{len(self._queue)} queued rolls remain unconsumed")
