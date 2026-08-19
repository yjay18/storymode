import io
import zipfile
from pathlib import Path

from scripts.import_book import import_book_to_draft

from campaign.builder.models import BuilderBrief
from campaign.importers import (
    EPUBImporter,
    SourceCompactor,
)
from campaign.storage.drafts import DraftRepository
from llm.prompts.campaign_generation_v1 import (
    render_areas_prompt,
    render_characters_prompt,
    render_meta_style_prompt,
    render_plot_prompt,
    render_skills_prompt,
    render_world_prompt,
)


def _create_sample_epub(tmp_path: Path) -> Path:
    """Create a sample EPUB with rich lore, culture, factions, and landmarks."""
    epub_path = tmp_path / "chronicles_of_valoria.epub"
    buf = io.BytesIO()
    ch1_html = (
        '<html xmlns="http://www.w3.org/1999/xhtml">\n'
        "<head><title>Chapter 1: The Iron Keep</title></head>\n"
        "<body>\n"
        "<h1>Chapter 1: The Iron Keep</h1>\n"
        "<p>Lord Dennis stood atop the battlements of Iron Keep.</p>\n"
        "<p>In Valoria, the ancient oath of hospitality was sacred law: "
        "no man could spill blood under the roof of his host.</p>\n"
        "<p>Lady Valerie whispered caution as the High Gate swung open.</p>\n"
        "</body>\n"
        "</html>"
    )
    ch2_html = (
        '<html xmlns="http://www.w3.org/1999/xhtml">\n'
        "<head><title>Chapter 2: Shadow of the Citadel</title></head>\n"
        "<body>\n"
        "<h1>Chapter 2: Shadow of the Citadel</h1>\n"
        "<p>Within the Sunken Citadel, blood magic demanded a heavy price.</p>\n"
        "<p>Commander Kaelen warned: Refined steel is scarce in these badlands, "
        "and every blade must be preserved.</p>\n"
        "</body>\n"
        "</html>"
    )
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
            <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
                <rootfiles>
                    <rootfile full-path="OEBPS/content.opf"
                              media-type="application/oebps-package+xml"/>
                </rootfiles>
            </container>""",
        )
        zf.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0"?>
            <package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
                <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
                    <dc:title>Chronicles of Valoria</dc:title>
                    <dc:creator>Archivist Brandon</dc:creator>
                </metadata>
                <manifest>
                    <item id="ch1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
                    <item id="ch2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
                </manifest>
                <spine>
                    <itemref idref="ch1"/>
                    <itemref idref="ch2"/>
                </spine>
            </package>""",
        )
        zf.writestr("OEBPS/chapter1.xhtml", ch1_html)
        zf.writestr("OEBPS/chapter2.xhtml", ch2_html)

    epub_path.write_bytes(buf.getvalue())
    return epub_path


def test_epub_two_pass_compactor(tmp_path: Path) -> None:
    """Verify that the two-pass compactor extracts culture, taboos, factions, and characters."""
    epub_file = _create_sample_epub(tmp_path)
    importer = EPUBImporter()
    doc = importer.import_file(epub_file)

    assert doc.title == "Chronicles of Valoria"
    assert len(doc.chunks) == 2

    compactor = SourceCompactor()
    codex = compactor.compact_document(doc)

    assert codex.source_title == "Chronicles of Valoria"
    assert len(codex.cultural_profiles) >= 1

    profile = codex.cultural_profiles[0]
    assert len(profile.taboos_and_oaths) >= 1
    assert len(profile.magic_and_supernatural_rules) >= 1
    assert len(profile.scarcity_and_economy) >= 1
    assert len(profile.attire_and_status) >= 1

    # Verify key areas and characters were extracted
    assert any("Keep" in a.name or "Citadel" in a.name for a in codex.primary_areas)
    assert any(
        c.canonical_name in ("Lord Dennis", "Lady Valerie", "Commander Kaelen")
        for c in codex.key_characters
    )


def test_cli_import_book_to_draft(tmp_path: Path) -> None:
    """Verify scripts/import_book.py creates a valid campaign draft in the repository."""
    epub_file = _create_sample_epub(tmp_path)
    campaigns_dir = tmp_path / "campaigns"
    campaigns_dir.mkdir()

    draft_id = import_book_to_draft(
        epub_file,
        genre="grimdark fantasy",
        tone="cold, gritty",
        campaigns_dir=campaigns_dir,
    )

    assert draft_id.startswith("draft_")

    repo = DraftRepository(tmp_path)
    draft = repo.load_draft(draft_id)

    assert draft.brief.title == "Chronicles of Valoria"
    assert draft.brief.genre == "grimdark fantasy"
    assert draft.brief.tone == "cold, gritty"
    assert draft.brief.source.source_type == "epub"
    assert len(draft.brief.protected_facts) > 0
    assert all(stage.status == "not_started" for stage in draft.stages.values())


def test_stage_prompts_include_cultural_context(tmp_path: Path) -> None:
    """Verify that all stage prompt templates inject the extracted cultural context."""
    epub_file = _create_sample_epub(tmp_path)
    importer = EPUBImporter()
    doc = importer.import_file(epub_file)
    compactor = SourceCompactor()
    codex = compactor.compact_document(doc)

    brief = BuilderBrief(
        title="Chronicles of Valoria",
        premise="An epic tale of survival.",
        protected_facts=["Guest right is sacred", "Refined steel is rare"],
    )

    meta_prompt = render_meta_style_prompt(brief, codex=codex)
    assert "Guest right" in meta_prompt or "Taboos & Oaths" in meta_prompt

    world_prompt = render_world_prompt(brief, codex=codex)
    assert "Taboos & Oaths" in world_prompt

    areas_prompt = render_areas_prompt(brief, codex=codex)
    assert "Taboos & Oaths" in areas_prompt

    plot_prompt = render_plot_prompt(brief, codex=codex)
    assert "Taboos & Oaths" in plot_prompt

    chars_prompt = render_characters_prompt(brief, codex=codex)
    assert "Taboos & Oaths" in chars_prompt

    skills_prompt = render_skills_prompt(brief, codex=codex)
    assert "Taboos & Oaths" in skills_prompt
