"""CLI tool to import an EPUB or text file into a Storymode campaign draft (BUILD-02)."""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

from campaign.builder.models import (
    ArtDirection,
    BuilderBrief,
    ContentBoundaries,
    SourceMetadata,
)
from campaign.builder.normalization import create_initial_draft_state
from campaign.importers.compactor import SourceCompactor
from campaign.importers.epub import EPUBImporter
from campaign.importers.plain_text import PlainTextImporter
from campaign.storage.drafts import DraftRepository
from domain.models.common import EntityId


def import_book_to_draft(
    file_path: Path,
    genre: str = "fantasy",
    tone: str = "grounded, atmospheric",
    campaigns_dir: Path | None = None,
) -> str:
    """Import an EPUB or plain text file, compact world lore, and create a draft."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix == ".epub":
        importer = EPUBImporter()
        doc = importer.import_file(file_path)
        source_type = "epub"
    elif suffix in (".txt", ".text", ".md", ".markdown"):
        txt_importer = PlainTextImporter()
        doc = txt_importer.import_file(file_path)
        source_type = "plain_text"
    else:
        raise ValueError(f"Unsupported format: '{suffix}'. Supported: .epub, .txt, .md")

    print(f"📖 Imported '{doc.title}': {len(doc.chunks)} chapters/chunks extracted.")
    print("⏳ Running two-pass world compactor to extract cultural profiles and lore...")

    compactor = SourceCompactor()
    codex = compactor.compact_document(doc)

    print(
        f"✨ Extracted {len(codex.cultural_profiles)} cultural profiles, "
        f"{len(codex.key_characters)} key NPCs, "
        f"{len(codex.primary_areas)} areas."
    )

    # Build concise protected lore facts
    protected_facts: list[str] = []
    for cp in codex.cultural_profiles[:3]:
        for taboo in cp.taboos_and_oaths[:2]:
            protected_facts.append(f"[{cp.region_name} Taboo] {taboo}")
        for magic in cp.magic_and_supernatural_rules[:2]:
            protected_facts.append(f"[{cp.region_name} Law] {magic}")

    summary_text = f"World adapted from '{doc.title}'. Regions: " + ", ".join(
        a.name for a in codex.primary_areas[:3]
    )

    brief = BuilderBrief(
        title=doc.title[:100],
        premise=(
            f"An adventure set in the world of {doc.title}. "
            "Explore factions, regional taboos, and ancient secrets."
        ),
        campaign_mode="faithful_story",
        genre=genre,
        tone=tone,
        source=SourceMetadata(
            source_type=source_type,  # type: ignore[arg-type]
            title=doc.title,
            raw_char_count=doc.total_chars,
        ),
        source_summary=summary_text[:4000],
        protected_facts=protected_facts[:10],
        content_boundaries=ContentBoundaries(),
        art_direction=ArtDirection(),
    )

    root_dir = (campaigns_dir or Path("campaigns")).resolve().parent
    repo = DraftRepository(root_dir)
    draft_id = EntityId(f"draft_{uuid.uuid4().hex[:8]}")
    draft = create_initial_draft_state(draft_id, brief)
    repo.save_draft(draft)

    return str(draft.draft_id)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import an EPUB or text book into a Storymode campaign draft."
    )
    parser.add_argument("file", type=Path, help="Path to .epub, .txt, or .md file")
    parser.add_argument("--genre", default="fantasy", help="Genre label (default: fantasy)")
    parser.add_argument(
        "--tone", default="grounded, atmospheric", help="Tone (default: grounded, atmospheric)"
    )

    args = parser.parse_args()

    try:
        draft_id = import_book_to_draft(args.file, genre=args.genre, tone=args.tone)
        print(f"\n🎉 Successfully created draft: {draft_id}")
        print(f"👉 Open in UI: http://127.0.0.1:5173/builder/drafts/{draft_id}")
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
