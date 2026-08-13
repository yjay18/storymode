"""Tests for campaign loading and fingerprinting."""

from engine.campaign import calculate_fingerprint


def test_calculate_fingerprint_deterministic() -> None:
    # Identical semantic content but different key order
    content_a = {
        "campaign.json": {"title": "Test", "schema_version": 1},
        "areas.json": {"areas": []},
    }
    content_b = {
        "areas.json": {"areas": []},
        "campaign.json": {"schema_version": 1, "title": "Test"},
    }
    
    assert calculate_fingerprint(content_a) == calculate_fingerprint(content_b)


def test_calculate_fingerprint_ignores_fingerprint_field() -> None:
    # The fingerprint field itself shouldn't change the fingerprint
    content_a = {
        "campaign.json": {"title": "Test"},
    }
    content_b = {
        "campaign.json": {"title": "Test", "content_fingerprint": "some-old-hash"},
    }
    
    assert calculate_fingerprint(content_a) == calculate_fingerprint(content_b)


def test_calculate_fingerprint_strings_vs_dicts() -> None:
    content_dict = {
        "campaign.json": {"title": "Test", "status": "published"},
    }
    content_str = {
        "campaign.json": '{"status": "published", "title": "Test"}',
    }
    
    assert calculate_fingerprint(content_dict) == calculate_fingerprint(content_str)
