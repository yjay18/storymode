"""Tests for random sources."""

from unittest.mock import patch

import pytest

from engine.dice.secure import SecureRandomSource
from engine.dice.testing import ScriptedRandomSource


def test_secure_random_source() -> None:
    source = SecureRandomSource()
    
    with pytest.raises(ValueError, match="sides must be >= 2"):
        source.roll(1)
        
    with patch("secrets.SystemRandom.randint", return_value=15) as mock_randint:
        result = source.roll(20)
        assert result == 15
        mock_randint.assert_called_once_with(1, 20)


def test_scripted_random_source() -> None:
    source = ScriptedRandomSource([10, 20, 5])
    
    # Check order
    assert source.roll(20) == 10
    assert source.roll(20) == 20
    assert source.roll(20) == 5
    
    assert source.call_count == 3
    source.assert_exhausted()
    
    # Check exhaustion
    with pytest.raises(RuntimeError, match="exhausted"):
        source.roll(20)
        
def test_scripted_random_source_bad_sides() -> None:
    source = ScriptedRandomSource([10])
    with pytest.raises(ValueError, match="sides must be >= 2"):
        source.roll(1)


def test_scripted_random_source_out_of_bounds() -> None:
    source = ScriptedRandomSource([21])
    with pytest.raises(ValueError, match="out of bounds"):
        source.roll(20)


def test_scripted_random_source_unexhausted() -> None:
    source = ScriptedRandomSource([10, 20])
    source.roll(20)
    with pytest.raises(AssertionError, match="1 queued rolls remain"):
        source.assert_exhausted()
