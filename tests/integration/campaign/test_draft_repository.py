"""Integration tests for DraftRepository (BUILD-03)."""

from pathlib import Path

import pytest

from campaign.builder import BuilderBrief, create_initial_draft_state
from campaign.storage.drafts import (
    DraftNotFoundError,
    DraftRepository,
    DraftRevisionConflictError,
)
from domain.models.common import EntityId
from engine.state.errors import UnsafePathError


@pytest.fixture
def repo(tmp_path: Path) -> DraftRepository:
    return DraftRepository(tmp_path)


def test_draft_save_and_load_roundtrip(repo: DraftRepository) -> None:
    brief = BuilderBrief(
        title="Test Campaign",
        premise="A kingdom under siege by ancient sorcery.",
    )
    draft = create_initial_draft_state(EntityId("draft-alpha"), brief)

    saved = repo.save_draft(draft)
    assert saved.revision == 1

    loaded = repo.load_draft(EntityId("draft-alpha"))
    assert loaded.draft_id == "draft-alpha"
    assert loaded.brief.title == "Test Campaign"
    assert loaded.revision == 1


def test_draft_revision_optimistic_concurrency(repo: DraftRepository) -> None:
    brief = BuilderBrief(title="Conflict Campaign", premise="A land divided.")
    draft = create_initial_draft_state(EntityId("draft-beta"), brief)

    saved_v1 = repo.save_draft(draft)
    assert saved_v1.revision == 1

    # Saving with matching expected_revision succeeds and increments revision
    saved_v2 = repo.save_draft(saved_v1, expected_revision=1)
    assert saved_v2.revision == 2

    # Saving with stale expected_revision fails
    with pytest.raises(DraftRevisionConflictError):
        repo.save_draft(saved_v2, expected_revision=1)


def test_draft_unsafe_path_rejection(repo: DraftRepository) -> None:
    with pytest.raises(UnsafePathError):
        repo.load_draft("../escape")

    with pytest.raises(UnsafePathError):
        repo.load_draft("nested/path")


def test_draft_not_found(repo: DraftRepository) -> None:
    with pytest.raises(DraftNotFoundError):
        repo.load_draft("does-not-exist")


def test_draft_cancel_and_delete(repo: DraftRepository) -> None:
    brief = BuilderBrief(title="Cancellable", premise="Premise here.")
    draft = create_initial_draft_state(EntityId("draft-cancel"), brief)
    repo.save_draft(draft)

    cancelled = repo.cancel_draft("draft-cancel")
    assert cancelled.revision == 2
    for st in cancelled.stages.values():
        assert st.status == "cancelled"

    assert repo.delete_draft("draft-cancel") is True
    assert repo.delete_draft("draft-cancel") is False
