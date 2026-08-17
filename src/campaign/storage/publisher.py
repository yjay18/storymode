"""Atomic publisher for validated campaign drafts (BUILD-08).

Guarantees:
- Requires complete error-free draft and explicit user confirmation flag.
- Computes canonical SHA-256 content fingerprint.
- Stages and atomically publishes to the campaigns directory.
- Rejects existing campaign IDs (immutable publication).
- Verifies newly installed pack via load_campaign before marking draft published.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

from campaign.builder.models import DraftStageState
from campaign.builder.review import DraftReviewService
from campaign.storage.drafts import DraftRepository
from domain.models.common import EntityId, FrozenModel
from engine.campaign import calculate_fingerprint, load_campaign
from engine.state.errors import UnsafePathError


class PublishError(Exception):
    """Base exception for campaign publishing errors."""


class UnconfirmedPublishError(PublishError):
    """Raised when publication is attempted without explicit user confirmation."""


class InvalidDraftPublishError(PublishError):
    """Raised when publishing a draft that is incomplete or contains errors."""


class CampaignAlreadyExistsError(PublishError):
    """Raised when attempting to publish over an existing published campaign."""


class PublishResult(FrozenModel):
    """Result of successfully publishing a campaign draft."""

    campaign_id: EntityId
    campaign_dir: Path
    fingerprint: str


class CampaignPublisher:
    """Publishes validated campaign drafts into immutable playable campaigns."""

    def __init__(
        self,
        campaigns_dir: Path | str,
        draft_repo: DraftRepository,
        review_service: DraftReviewService,
    ) -> None:
        self.campaigns_dir = Path(campaigns_dir).resolve()
        self.campaigns_dir.mkdir(parents=True, exist_ok=True)
        self.draft_repo = draft_repo
        self.review_service = review_service

    def publish_draft(
        self,
        draft_id: EntityId | str,
        confirmed: bool = False,
    ) -> PublishResult:
        """Publish a validated draft atomically into an immutable campaign pack."""
        if not confirmed:
            raise UnconfirmedPublishError(
                "Publishing requires explicit user confirmation (confirmed=True)"
            )

        # 1. Validate draft completeness and correctness
        report = self.review_service.validate_draft(draft_id)
        if not report.is_publish_ready:
            error_msgs = "; ".join(f"[{e.stage}] {e.message}" for e in report.errors)
            raise InvalidDraftPublishError(f"Draft '{draft_id}' is not publish-ready: {error_msgs}")

        draft = self.draft_repo.load_draft(draft_id)
        meta_data = draft.stages["meta_style"].artifact_data
        if not meta_data or "meta" not in meta_data:
            raise InvalidDraftPublishError("Draft missing meta artifact data")

        campaign_id = EntityId(str(meta_data["meta"]["campaign_id"]))

        # Validate campaign ID safety
        if ".." in campaign_id or "/" in campaign_id or "\\" in campaign_id:
            raise UnsafePathError(f"Unsafe campaign ID: '{campaign_id}'")

        target_dir = self.campaigns_dir / campaign_id
        if target_dir.exists():
            raise CampaignAlreadyExistsError(
                f"Campaign '{campaign_id}' is already published and immutable"
            )

        # 2. Assemble canonical files and compute fingerprint
        file_contents = self.review_service._assemble_draft_files(draft)

        # Update campaign.json status to published
        camp_dict = json.loads(file_contents["campaign.json"])
        camp_dict["status"] = "published"
        camp_dict.pop("content_fingerprint", None)
        file_contents["campaign.json"] = json.dumps(camp_dict)

        # Calculate canonical SHA-256 fingerprint
        fingerprint = calculate_fingerprint(file_contents)
        camp_dict["content_fingerprint"] = fingerprint
        file_contents["campaign.json"] = json.dumps(camp_dict, indent=2)

        # 3. Stage in temporary sibling directory
        staging_dir = self.campaigns_dir / f".staging_{campaign_id}_{uuid.uuid4().hex[:8]}"
        staging_dir.mkdir(parents=True, exist_ok=True)

        try:
            for filename, content in file_contents.items():
                file_path = staging_dir / filename
                with file_path.open("w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())

            # 4. Atomic directory publication
            os.replace(staging_dir, target_dir)

            # 5. Verify published pack through authoritative engine loader
            pack, diags = load_campaign(target_dir)
            if pack is None or diags:
                diag_str = "; ".join(f"[{d.code}] {d.message}" for d in diags)
                shutil.rmtree(target_dir, ignore_errors=True)
                raise PublishError(f"Verification of published campaign failed: {diag_str}")

            # 6. Mark draft published
            updated_stages = dict(draft.stages)
            review_state = draft.stages.get(
                "review", DraftStageState(stage="review", status="valid")
            )
            updated_stages["review"] = review_state.model_copy(update={"status": "valid"})
            self.draft_repo.save_draft(
                draft.model_copy(
                    update={
                        "is_published": True,
                        "published_campaign_id": campaign_id,
                        "stages": updated_stages,
                    }
                ),
                expected_revision=draft.revision,
            )

            return PublishResult(
                campaign_id=campaign_id,
                campaign_dir=target_dir,
                fingerprint=fingerprint,
            )

        except Exception:
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)
            raise
