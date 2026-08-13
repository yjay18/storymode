"""Architecture import boundary tests."""

import ast
from pathlib import Path

import pytest


def get_imports(filepath: Path, src_root: Path) -> set[str]:
    """Parse a Python file and return all imported module names."""
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))
    except SyntaxError:
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.level > 0:
                try:
                    parts = list(filepath.relative_to(src_root).parts[:-1])
                    for _ in range(node.level - 1):
                        if parts:
                            parts.pop()
                    base = ".".join(parts)
                    module = f"{base}.{node.module}" if base else node.module
                except ValueError:
                    module = node.module
            else:
                module = node.module
            imports.add(module)
    return imports


def check_violations(package_dir: Path, src_root: Path, forbidden: list[str]) -> list[str]:
    """Check a directory for forbidden imports."""
    violations: list[str] = []
    if not package_dir.exists():
        return violations

    for filepath in package_dir.rglob("*.py"):
        imports = get_imports(filepath, src_root)
        for imp in imports:
            for bad in forbidden:
                if imp == bad or imp.startswith(f"{bad}."):
                    try:
                        rel = filepath.relative_to(src_root)
                    except ValueError:
                        rel = filepath
                    violations.append(f"{rel} imports {imp}")
    return violations


@pytest.fixture
def src_root() -> Path:
    """Return the src directory path."""
    return Path(__file__).parent.parent.parent / "src"


def test_domain_boundaries(src_root: Path) -> None:
    """Domain cannot import other project packages, FastAPI, or HTTPX."""
    forbidden = ["api", "app", "campaign", "engine", "llm", "fastapi", "httpx"]
    violations = check_violations(src_root / "domain", src_root, forbidden)
    assert not violations, f"Domain boundary violations: {violations}"


def test_engine_boundaries(src_root: Path) -> None:
    """Engine cannot import app, api, campaign, llm, or FastAPI."""
    forbidden = ["api", "app", "campaign", "llm", "fastapi"]
    violations = check_violations(src_root / "engine", src_root, forbidden)
    assert not violations, f"Engine boundary violations: {violations}"


def test_llm_boundaries(src_root: Path) -> None:
    """LLM cannot import api, app, or concrete state/campaign storage modules."""
    forbidden = ["api", "app", "campaign.storage", "engine.state"]
    violations = check_violations(src_root / "llm", src_root, forbidden)
    assert not violations, f"LLM boundary violations: {violations}"


def test_api_boundaries(src_root: Path) -> None:
    """API cannot import rule submodules."""
    forbidden = ["domain.rules"]
    violations = check_violations(src_root / "api", src_root, forbidden)
    assert not violations, f"API boundary violations: {violations}"


def test_parser_detects_violations(tmp_path: Path) -> None:
    """Verify that the AST parser actually catches forbidden imports."""
    # Create fake src tree
    src = tmp_path / "src"
    domain = src / "domain"
    domain.mkdir(parents=True)

    # Write a file with a forbidden import
    bad_file = domain / "bad.py"
    bad_file.write_text(
        "import fastapi\nfrom api.routes import user\nfrom ..engine import core\n",
        encoding="utf-8",
    )

    violations = check_violations(domain, src, ["fastapi", "api", "engine"])
    assert len(violations) == 3, f"Expected 3 violations, got {len(violations)}"
    assert any("imports fastapi" in v for v in violations)
    assert any("imports api.routes" in v for v in violations)
    assert any("imports engine" in v for v in violations)
