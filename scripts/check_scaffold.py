"""Check scaffold validation script."""

import argparse
import re
import sys
from pathlib import Path


def check_required_docs(root: Path) -> list[str]:
    """Verify that all required context and agent manuals exist."""
    errors = []

    for req in ["CONTEXT.md", "AGENT.md", "README.md", "IMPLEMENTATION_CHECKLIST.md"]:
        if not (root / req).is_file():
            errors.append(f"Missing required file: {req}")

    for base in ["docs", "scripts", "src", "tests"]:
        base_dir = root / base
        if not base_dir.is_dir():
            continue

        for path in [base_dir, *list(base_dir.rglob("*"))]:
            if path.is_dir() and path.name != "__pycache__":
                for req in ["CONTEXT.md", "AGENT.md"]:
                    if not (path / req).is_file():
                        rel = (path / req).relative_to(root)
                        errors.append(f"Missing required file: {rel}")

    return sorted(set(errors))


def check_markdown_links(root: Path) -> list[str]:
    """Verify that relative markdown links are valid."""
    errors = []
    link_pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

    for md_file in root.rglob("*.md"):
        if any(part.startswith(".") and part != "." for part in md_file.parts):
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for match in link_pattern.finditer(content):
            link = match.group(1).split("#")[0]
            if not link or link.startswith(("http://", "https://", "mailto:")):
                continue

            target = (md_file.parent / link).resolve()
            if not target.exists():
                rel_file = md_file.relative_to(root)
                errors.append(f"Broken link in {rel_file}: {link}")

    return sorted(errors)


def run_checks(root: Path) -> int:
    """Run all checks and print errors."""
    errors = check_required_docs(root) + check_markdown_links(root)

    if errors:
        for error in errors:
            print(error)
        return 1

    print("Scaffold checks passed.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate documentation scaffold.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Root directory to check")
    args = parser.parse_args()

    sys.exit(run_checks(args.root))
