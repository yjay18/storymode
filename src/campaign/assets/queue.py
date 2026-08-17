"""Single-worker bounded queue and deduplication for local image rendering."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from llm.contracts.image import ImageResult


class AssetGenerationQueue:
    """Async single-worker queue ensuring bounded local resources and deduplicating key requests."""

    def __init__(self, max_concurrent: int = 1) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._in_flight: dict[str, asyncio.Task[ImageResult]] = {}
        self._lock = asyncio.Lock()

    async def enqueue_or_join(
        self,
        asset_key: str,
        generate_fn: Callable[[], Coroutine[Any, Any, ImageResult]],
    ) -> ImageResult:
        """Enqueue generation task or join in-flight task if same key is rendering."""
        async with self._lock:
            if asset_key in self._in_flight:
                task = self._in_flight[asset_key]
                if not task.done():
                    return await task

            # Create new task
            async def _worker() -> ImageResult:
                async with self._semaphore:
                    return await generate_fn()

            task = asyncio.create_task(_worker())
            self._in_flight[asset_key] = task

        try:
            result = await task
            return result
        finally:
            async with self._lock:
                if asset_key in self._in_flight and self._in_flight[asset_key] is task:
                    del self._in_flight[asset_key]

    async def cancel_key(self, asset_key: str) -> bool:
        """Cancel an in-flight rendering task if active."""
        async with self._lock:
            if asset_key in self._in_flight:
                task = self._in_flight[asset_key]
                task.cancel()
                del self._in_flight[asset_key]
                return True
        return False
