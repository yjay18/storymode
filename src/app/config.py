"""Application configuration."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    log_level: str = Field(default="INFO")

    @field_validator("host", "ollama_url")
    @classmethod
    def require_loopback(cls, v: str) -> str:
        """Ensure host and Ollama URL use loopback addresses."""
        v_lower = v.lower()
        if "127.0.0.1" not in v_lower and "localhost" not in v_lower:
            raise ValueError("Must use a loopback address (127.0.0.1 or localhost)")
        return v


def get_settings() -> Settings:
    """Dependency to provide application settings."""
    return Settings()
