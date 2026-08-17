"""Unit tests for SourceCompactor (BUILD-02)."""

from campaign.importers import (
    ImportedDocument,
    SourceChunk,
    SourceCompactor,
)


def test_source_compactor_synthesizes_world_codex() -> None:
    chunks = [
        SourceChunk(
            index=1,
            title="Chapter 1",
            text=(
                "Lord Brandon stood upon the battlements of Winterhold Castle, "
                "swearing an oath before his warriors."
            ),
            char_count=100,
        ),
        SourceChunk(
            index=2,
            title="Chapter 2",
            text=(
                "The ancient laws of the realm demanded guest right, "
                "while rumors of dark magic spread through the lower vaults."
            ),
            char_count=110,
        ),
    ]

    doc = ImportedDocument(
        title="A Tale of Two Keeps",
        source_type="epub",
        total_chars=210,
        chunks=chunks,
    )

    compactor = SourceCompactor()
    codex = compactor.compact_document(
        doc, custom_prompt="Play as a hedge knight seeking redemption."
    )

    assert codex.source_title == "A Tale of Two Keeps"
    assert codex.source_type == "epub"
    assert "hedge knight seeking redemption" in codex.core_premise
    assert len(codex.cultural_profiles) >= 1

    profile = codex.cultural_profiles[0]
    assert len(profile.taboos_and_oaths) >= 1
    assert len(profile.superstitions_and_omens) >= 1
    assert len(profile.scarcity_and_economy) >= 1
    assert len(profile.attire_and_status) >= 1
    assert len(profile.magic_and_supernatural_rules) >= 1

    assert len(codex.primary_areas) >= 1
    assert len(codex.major_factions) >= 1
