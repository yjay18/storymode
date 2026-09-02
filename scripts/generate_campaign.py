"""Headless campaign generation: quick prompt -> all stages -> validate -> publish.

Runs the same builder pipeline the web UI uses, against the local Ollama configured
by ``STORYMODE_*`` settings. Used to produce the bundled sample campaign and by the
first-run script when the campaign library is empty.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

from app.config import Settings
from campaign.builder.models import ALL_DRAFT_STAGES, QuickPromptInput
from campaign.builder.normalization import create_initial_draft_state, normalize_quick_prompt
from campaign.builder.review import DraftReviewService
from campaign.generation.orchestrator import GenerationOrchestrator
from campaign.generation.stages import StageRunner
from campaign.storage.drafts import DraftRepository
from campaign.storage.publisher import CampaignPublisher
from domain.models.common import EntityId
from llm.ollama_client import OllamaClient


async def generate_and_publish(
    premise: str,
    title: str | None,
    settings: Settings,
    draft_id: str | None = None,
) -> Path:
    """Create (or resume) a draft, run every stage, validate, and publish. Returns pack dir."""
    campaigns_dir = Path(settings.campaigns_dir).resolve()
    repo = DraftRepository(campaigns_dir.parent)
    client = OllamaClient(
        base_url=settings.ollama_url,
        default_timeout=settings.ollama_timeout_seconds,
        max_response_bytes=settings.ollama_max_response_bytes,
    )
    orchestrator = GenerationOrchestrator(StageRunner(client, repo, settings.model_text), repo)

    if draft_id is None:
        draft_id = f"draft-{uuid.uuid4().hex[:8]}"
        brief = normalize_quick_prompt(QuickPromptInput(premise=premise, title=title))
        repo.save_draft(create_initial_draft_state(EntityId(draft_id), brief))
        print(f"draft {draft_id}: '{brief.title}' using model {settings.model_text}")
    else:
        print(f"resuming draft {draft_id} using model {settings.model_text}")

    draft = await orchestrator.generate_all(draft_id)
    for name, stage in draft.stages.items():
        print(f"  stage {name:<11} {stage.status:<8} attempts={stage.attempts}")
        for diag in stage.diagnostics[:3]:
            print(f"    - {diag.message[:300]}")

    review = DraftReviewService(repo)
    report = review.validate_draft(draft_id)
    if not report.is_publish_ready:
        for err in report.errors[:20]:
            print(f"  [{err.stage}] {err.message}")
        raise SystemExit(f"draft {draft_id} is not publish-ready; re-run with --draft {draft_id}")

    result = CampaignPublisher(campaigns_dir, repo, review).publish_draft(draft_id, confirmed=True)
    print(f"published {result.campaign_id} -> {result.campaign_dir} ({result.fingerprint[:12]})")
    return result.campaign_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="Stages run in order: " + ", ".join(ALL_DRAFT_STAGES),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("premise", nargs="?", help="Campaign premise (omit when using --draft)")
    parser.add_argument("--title", default=None)
    parser.add_argument("--draft", default=None, help="Resume an existing draft id")
    args = parser.parse_args()
    if args.premise is None and args.draft is None:
        parser.error("a premise or --draft is required")
    try:
        asyncio.run(generate_and_publish(args.premise or "", args.title, Settings(), args.draft))
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
