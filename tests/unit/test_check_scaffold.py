"""Tests for the check_scaffold script."""

import shutil
from pathlib import Path

from scripts.check_scaffold import check_markdown_links, check_required_docs


def test_check_scaffold_valid_repo() -> None:
    """Valid repo passes without errors."""
    root = Path(__file__).parent.parent.parent
    errors = check_required_docs(root) + check_markdown_links(root)
    assert not errors, f"Expected no errors, got: {errors}"


def test_tmp_copied_scaffold_missing_file(tmp_path: Path) -> None:
    """Tmp copied scaffold missing a required root file fails with that relative path."""
    root = Path(__file__).parent.parent.parent

    for f in ["README.md", "IMPLEMENTATION_CHECKLIST.md"]:
        shutil.copy(root / f, tmp_path / f)

    target = tmp_path / "README.md"
    target.unlink()

    errors = check_required_docs(tmp_path)
    assert any("README.md" in e for e in errors)


def test_broken_local_link_fails(tmp_path: Path) -> None:
    """Broken local link fails deterministically."""
    doc = tmp_path / "broken.md"
    doc.write_text("[bad link](does_not_exist.md)")

    errors = check_markdown_links(tmp_path)
    assert any("does_not_exist.md" in e for e in errors)
