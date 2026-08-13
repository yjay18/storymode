"""Tests for application settings."""

import os
from pydantic import ValidationError
import pytest
from app.config import Settings, get_settings


def test_settings_defaults() -> None:
    """Settings have safe local defaults."""
    # Ensure environment variables don't pollute the default test
    env_vars = ["STORYMODE_HOST", "STORYMODE_PORT", "STORYMODE_CAMPAIGNS_DIR"]
    for var in env_vars:
        if var in os.environ:
            del os.environ[var]
            
    settings = Settings()
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.campaigns_dir == "./campaigns"
    assert settings.ollama_url == "http://127.0.0.1:11434"
    assert settings.model_text == "llama3.1:8b" # example explicit model name
    assert settings.model_image == "stable-diffusion" # example explicit model name
    assert settings.log_level == "INFO"


def test_settings_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings can be overridden by STORYMODE_ prefixed env vars."""
    monkeypatch.setenv("STORYMODE_PORT", "9000")
    monkeypatch.setenv("STORYMODE_LOG_LEVEL", "DEBUG")
    
    settings = Settings()
    assert settings.port == 9000
    assert settings.log_level == "DEBUG"


def test_settings_rejections(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings reject invalid values like non-loopback hosts."""
    monkeypatch.setenv("STORYMODE_HOST", "0.0.0.0")
    with pytest.raises(ValidationError) as exc:
        Settings()
    assert "loopback" in str(exc.value).lower()
