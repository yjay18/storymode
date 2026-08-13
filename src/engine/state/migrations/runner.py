"""Migration runner."""

from engine.state.migrations.registry import MigrationRegistry


class MigrationRunner:
    """Runs sequential migrations on a state dictionary."""
    
    def __init__(self, registry: MigrationRegistry) -> None:
        self.registry = registry
        
    def run_migrations(self, state: dict, target_version: int = 1) -> dict:
        """Run migrations to upgrade the state dictionary to target_version."""
        current_version = state.get("schema_version", 0)
        
        if current_version < 1:
            raise ValueError(f"Unsupported schema version: {current_version}")
            
        if current_version > target_version:
            raise ValueError(f"State schema version {current_version} is newer than target {target_version}")
            
        if current_version == target_version:
            return state # No-op
            
        # Run sequential steps
        migrated = dict(state)
        for v in range(current_version + 1, target_version + 1):
            step = self.registry.get_step(v)
            if not step:
                raise ValueError(f"Missing migration step for version {v}")
            migrated = step(migrated)
            migrated["schema_version"] = v
            
        return migrated
