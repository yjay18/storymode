"""Campaign loading and fingerprinting."""

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from domain.models.diagnostics import Diagnostic
from domain.models.pack import CampaignPack
from engine.validation.balance import validate_balance
from engine.validation.campaign_files import validate_campaign_files
from engine.validation.graphs import validate_graphs
from engine.validation.references import index_campaign_entities, validate_references


def calculate_fingerprint(file_contents: Mapping[str, Any]) -> str:
    """Calculate the canonical SHA-256 fingerprint of a campaign.

    The fingerprint is calculated from canonical JSON bytes for every design file,
    except the `content_fingerprint` field itself, ordered by filename.
    """
    hasher = hashlib.sha256()

    # Process files in deterministic alphabetical order
    for filename in sorted(file_contents.keys()):
        content = file_contents[filename]

        # Parse if it's a string
        parsed = json.loads(content) if isinstance(content, str) else dict(content)

        # Strip content_fingerprint if it exists
        if filename == "campaign.json" and "content_fingerprint" in parsed:
            del parsed["content_fingerprint"]

        # Canonical JSON string (sorted keys, no spaces)
        canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"))

        # Append filename and canonical content
        hasher.update(filename.encode("utf-8"))
        hasher.update(b":")
        hasher.update(canonical.encode("utf-8"))
        hasher.update(b"\n")

    return hasher.hexdigest()


def load_campaign(campaign_dir: Path) -> tuple[CampaignPack | None, list[Diagnostic]]:
    """Load and validate a campaign from a directory.

    Returns the valid CampaignPack and an empty list, or None and a list of diagnostics.
    """
    file_contents: dict[str, str] = {}
    diagnostics: list[Diagnostic] = []

    # Phase 1: Load files
    for file_path in campaign_dir.glob("*.json"):
        try:
            with open(file_path, encoding="utf-8") as f:
                file_contents[file_path.name] = f.read()
        except OSError as e:
            diagnostics.append(
                Diagnostic(
                    code="read_error",
                    file=file_path.name,
                    json_pointer="/",
                    message=f"Failed to read file: {e}",
                )
            )

    if diagnostics:
        return None, diagnostics

    pack, parse_diags = validate_campaign_files(file_contents)
    if pack is None:
        return None, parse_diags

    # Phase 2: Verify fingerprint if published
    from domain.models.campaign_meta import CampaignStatus

    if pack.meta.status == CampaignStatus.PUBLISHED:
        expected = pack.meta.content_fingerprint
        actual = calculate_fingerprint(file_contents)
        if expected != actual:
            diagnostics.append(
                Diagnostic(
                    code="fingerprint_mismatch",
                    file="campaign.json",
                    json_pointer="/content_fingerprint",
                    message=f"Campaign fingerprint mismatch. Expected {expected}, got {actual}",
                )
            )
            return None, diagnostics

    # Phase 3: References
    index, ref_diags = index_campaign_entities(pack)
    diagnostics.extend(ref_diags)
    if ref_diags:
        return None, diagnostics

    diagnostics.extend(validate_references(pack, index))

    # Phase 4: Graphs
    diagnostics.extend(validate_graphs(pack))

    # Phase 5: Balance
    diagnostics.extend(validate_balance(pack))

    if diagnostics:
        return None, sorted(diagnostics)

    return pack, []
