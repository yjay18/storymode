"""Local image generation adapter communicating strictly with local Ollama capability."""

from __future__ import annotations

import httpx

from llm.contracts.image import ImageCapability, ImagePrompt
from llm.health import ModelCapabilityStatus, check_ollama_health


class ImageGenerationError(Exception):
    """Base exception for local image generation errors."""


class ImageModelUnavailableError(ImageGenerationError):
    """Raised when no local image generation model is installed or running."""


class ImageGenerationTimeoutError(ImageGenerationError):
    """Raised when local image generation exceeds timeout threshold."""


class LocalImageGenerator:
    """Adapter executing local image generation prompts via loopback capability."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._ollama_url = ollama_url.rstrip("/")
        self._timeout = timeout_seconds

    async def probe_capability(self, image_model: str | None = None) -> ImageCapability:
        """Probe local Ollama instance for image generation model support."""
        try:
            health = await check_ollama_health(
                ollama_url=self._ollama_url,
                image_model=image_model,
            )
            is_available = health.image_status == ModelCapabilityStatus.AVAILABLE
            return ImageCapability(
                available=is_available,
                model_name=image_model if is_available else None,
            )
        except Exception:
            return ImageCapability(available=False)

    async def generate_image(
        self,
        prompt: ImagePrompt,
        capability: ImageCapability,
    ) -> bytes:
        """Render an image prompt using the local Ollama/diffusion capability."""
        if not capability.available or not capability.model_name:
            raise ImageModelUnavailableError(
                "Local image generation capability is unavailable or not configured"
            )

        payload = {
            "model": capability.model_name,
            "prompt": prompt.positive_prompt,
            "negative_prompt": prompt.negative_prompt,
            "options": {
                "width": prompt.width,
                "height": prompt.height,
            },
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._ollama_url}/api/generate_image",
                    json=payload,
                )
                if response.status_code == 404:
                    # Endpoint unsupported
                    raise ImageModelUnavailableError(
                        "Local model backend does not support image generation API"
                    )
                if response.status_code != 200:
                    raise ImageGenerationError(
                        f"Image generation failed with status {response.status_code}"
                    )
                return response.content
        except httpx.TimeoutException as err:
            raise ImageGenerationTimeoutError("Image generation timed out") from err
        except httpx.RequestError as err:
            raise ImageModelUnavailableError(
                f"Failed to connect to local image generator: {err}"
            ) from err
