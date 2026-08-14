"""Tests for migration runner."""

import pytest

from engine.state.migrations.registry import MigrationRegistry
from engine.state.migrations.runner import MigrationRunner


def test_migration_runner_noop() -> None:
    registry = MigrationRegistry()
    runner = MigrationRunner(registry)
    state = {"schema_version": 1, "data": "foo"}
    result = runner.run_migrations(state, target_version=1)
    assert result is state


def test_migration_runner_newer() -> None:
    registry = MigrationRegistry()
    runner = MigrationRunner(registry)
    state = {"schema_version": 2, "data": "foo"}
    with pytest.raises(ValueError, match="is newer than target"):
        runner.run_migrations(state, target_version=1)


def test_migration_runner_zero() -> None:
    registry = MigrationRegistry()
    runner = MigrationRunner(registry)
    state = {"schema_version": 0, "data": "foo"}
    with pytest.raises(ValueError, match="Unsupported schema version"):
        runner.run_migrations(state, target_version=1)


def test_migration_runner_steps() -> None:
    registry = MigrationRegistry()
    registry.register(2, lambda s: {**s, "added_by_v2": True})
    registry.register(3, lambda s: {**s, "added_by_v3": True})

    runner = MigrationRunner(registry)
    state = {"schema_version": 1, "data": "foo"}

    result = runner.run_migrations(state, target_version=3)
    assert result["schema_version"] == 3
    assert result["added_by_v2"] is True
    assert result["added_by_v3"] is True


def test_migration_runner_missing_step() -> None:
    registry = MigrationRegistry()
    registry.register(3, lambda s: {**s, "added_by_v3": True})

    runner = MigrationRunner(registry)
    state = {"schema_version": 1, "data": "foo"}

    with pytest.raises(ValueError, match="Missing migration step for version 2"):
        runner.run_migrations(state, target_version=3)
