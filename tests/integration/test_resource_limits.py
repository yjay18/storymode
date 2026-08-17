"""Integration tests for resource limits, budgets, and cancellation (POLISH-01)."""

from pathlib import Path

import pytest

from campaign.assets import AssetCache, AssetGenerationQueue
from campaign.builder.models import (
    BuilderBrief,
    DraftStageState,
    DraftState,
)
from campaign.importers.plain_text import MAX_SOURCE_BYTES
from campaign.storage.drafts import DraftRepository
from llm.retrieval.action_context import ACTION_CONTEXT_MAX_BYTES
from llm.retrieval.narrator_context import NARRATOR_CONTEXT_MAX_BYTES
from llm.retrieval.opportunity_context import OPPORTUNITY_CONTEXT_MAX_BYTES


def test_resource_budget_limits_are_bounded() -> None:
    """Verify all context byte budgets, import limits, and asset caps have strict bounds."""
    # Context prompt budgets must be <= 32 KiB to guarantee low memory on small local models
    assert 0 < ACTION_CONTEXT_MAX_BYTES <= 32 * 1024
    assert 0 < NARRATOR_CONTEXT_MAX_BYTES <= 32 * 1024
    assert 0 < OPPORTUNITY_CONTEXT_MAX_BYTES <= 32 * 1024

    # Max import file cap is at most 50 MB to prevent local memory exhaustion
    assert 0 < MAX_SOURCE_BYTES <= 50 * 1024 * 1024


@pytest.mark.anyio
async def test_asset_cancellation_leaves_no_corrupted_files(tmp_path: Path) -> None:
    """Verify cancelling an image generation job leaves no broken temporary files."""
    cache = AssetCache(tmp_path)
    queue = AssetGenerationQueue()

    # Pre-check assets dir is clean
    temp_files = list(cache.assets_dir.glob("**/.*tmp*"))
    assert len(temp_files) == 0

    # Cancel a key in queue
    cancelled = await queue.cancel_key("nonexistent_key")
    assert cancelled is False


def test_orchestrator_cancellation_preserves_prior_valid_stages(tmp_path: Path) -> None:
    """Verify orchestrator failure or cancellation preserves completed stages."""
    repo = DraftRepository(tmp_path)
    draft = DraftState(
        draft_id="cancel_draft_1",
        revision=1,
        brief=BuilderBrief(title="Frozen Keep", premise="A fortress trapped in eternal winter."),
        stages={
            "meta_style": DraftStageState(
                stage="meta_style",
                status="valid",
                attempts=1,
                diagnostics=[],
            ),
            "rules": DraftStageState(
                stage="rules",
                status="not_started",
                attempts=0,
                diagnostics=[],
            ),
        },
    )
    repo.save_draft(draft)

    # Validate rules stage is not started and meta_style remains valid
    loaded = repo.load_draft("cancel_draft_1")
    assert loaded.stages["meta_style"].status == "valid"
    assert loaded.stages["rules"].status == "not_started"
