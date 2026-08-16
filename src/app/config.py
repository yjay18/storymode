"""Application configuration."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from llm.health import is_loopback_host, validate_ollama_url


class Settings(BaseSettings):
    """Global application settings with STORYMODE_ prefix."""

    model_config = SettingsConfigDict(
        env_prefix="STORYMODE_",
        env_file=".env",
        extra="ignore",
    )

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    campaigns_dir: str = Field(default="./campaigns")
    ollama_url: str = Field(default="http://127.0.0.1:11434")
    model_text: str = Field(default="llama3.1:8b")
    model_image: str = Field(default="stable-diffusion")
    ollama_timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    ollama_max_response_bytes: int = Field(default=1024 * 1024, ge=1024)
    log_level: str = Field(default="INFO")

    @field_validator("host")
    @classmethod
    def require_loopback_host(cls, v: str) -> str:
        """Ensure host uses a valid loopback address."""
        if not is_loopback_host(v):
            raise ValueError(f"Host must be a local loopback address, got '{v}'")
        return v

    @field_validator("ollama_url")
    @classmethod
    def require_loopback_ollama_url(cls, v: str) -> str:
        """Ensure Ollama URL is http on a loopback host with no userinfo, query, or fragment."""
        return validate_ollama_url(v)


def get_settings() -> Settings:
    """Dependency to provide application settings."""
    return Settings()
