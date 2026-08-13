"""Pytest fixtures for storymode tests."""

import datetime
from collections.abc import Callable, Generator
from pathlib import Path

import pytest


@pytest.fixture
def fixed_clock() -> datetime.datetime:
    """Return a fixed UTC datetime for testing."""
    return datetime.datetime(2026, 8, 12, 12, 0, 0, tzinfo=datetime.UTC)


@pytest.fixture
def sequential_id_generator() -> Callable[[], str]:
    """Return a function that generates sequential predictable IDs."""

    def generator() -> Generator[str, None, None]:
        counter = 1
        while True:
            yield f"test-id-{counter:04d}"
            counter += 1

    gen = generator()
    return lambda: next(gen)


@pytest.fixture
def temp_campaign_root(tmp_path: Path) -> Path:
    """Provide a temporary directory for campaign data."""
    return tmp_path / "campaign"
