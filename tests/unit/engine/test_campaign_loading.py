"""Tests for campaign loading."""

import json
from pathlib import Path

from engine.campaign import calculate_fingerprint, load_campaign


def test_load_campaign_valid(tmp_path: Path) -> None:
    # Use valid-minimal fixture
    fixture_dir = Path(__file__).parent.parent.parent / "fixtures" / "campaigns" / "valid-minimal"
    
    pack, diagnostics = load_campaign(fixture_dir)
    assert not diagnostics
    assert pack is not None
    assert pack.meta.campaign_id == "minimal-campaign"


def test_load_campaign_fingerprint_mismatch(tmp_path: Path) -> None:
    # Copy valid-minimal but publish it with a bad fingerprint
    fixture_dir = Path(__file__).parent.parent.parent / "fixtures" / "campaigns" / "valid-minimal"
    
    for f in fixture_dir.glob("*.json"):
        dest = tmp_path / f.name
        dest.write_text(f.read_text())
        
    campaign_file = tmp_path / "campaign.json"
    meta = json.loads(campaign_file.read_text())
    meta["status"] = "published"
    meta["content_fingerprint"] = "a" * 64
    campaign_file.write_text(json.dumps(meta))
    
    pack, diagnostics = load_campaign(tmp_path)
    
    assert pack is None
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "fingerprint_mismatch"


def test_load_campaign_fingerprint_match(tmp_path: Path) -> None:
    # Publish with correct fingerprint
    fixture_dir = Path(__file__).parent.parent.parent / "fixtures" / "campaigns" / "valid-minimal"
    
    file_contents = {}
    for f in fixture_dir.glob("*.json"):
        dest = tmp_path / f.name
        content = f.read_text()
        dest.write_text(content)
        file_contents[f.name] = content
        
    # Calculate correct fingerprint (excluding the field itself if it were there)
    # but wait, calculating it requires we set status="published" first
    campaign_file = tmp_path / "campaign.json"
    meta = json.loads(campaign_file.read_text())
    meta["status"] = "published"
    # Write back without fingerprint so calculate_fingerprint sees published status
    campaign_file.write_text(json.dumps(meta))
    file_contents["campaign.json"] = json.dumps(meta)
    
    correct_hash = calculate_fingerprint(file_contents)
    
    # Now set the content fingerprint
    meta["content_fingerprint"] = correct_hash
    campaign_file.write_text(json.dumps(meta))
    
    pack, diagnostics = load_campaign(tmp_path)
    
    assert pack is not None
    assert not diagnostics
