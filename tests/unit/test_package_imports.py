"""Smoke test for package imports."""

import logging

import pytest


def test_packages_import_without_side_effects(caplog: pytest.LogCaptureFixture) -> None:
    """Test that all top-level packages can be imported without logging side effects."""
    with caplog.at_level(logging.DEBUG):
        import api  # noqa: F401
        import app  # noqa: F401
        import campaign  # noqa: F401
        import domain  # noqa: F401
        import engine  # noqa: F401
        import llm  # noqa: F401

    assert not caplog.records, "Imports should not emit logs."
