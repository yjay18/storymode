"""Migration registry."""

from collections.abc import Callable
from typing import Any

MigrationStep = Callable[[dict[str, Any]], dict[str, Any]]

class MigrationRegistry:
    """Registry of schema migration steps."""
    
    def __init__(self) -> None:
        self._steps: dict[int, MigrationStep] = {}
        
    def register(self, target_version: int, step: MigrationStep) -> None:
        """Register a migration step that upgrades FROM target_version - 1 TO target_version."""
        self._steps[target_version] = step
        
    def get_step(self, target_version: int) -> MigrationStep | None:
        """Get the migration step for a target version."""
        return self._steps.get(target_version)
        
    def get_max_version(self) -> int:
        """Get the maximum supported schema version."""
        if not self._steps:
            return 1
        return max(self._steps.keys())

# Global registry for standard engine migrations.
# Currently v1 is the only version, so no steps are registered.
default_registry = MigrationRegistry()
