"""Tests for entity resolver."""

import pytest

from engine.actions.candidates import Candidate, CandidateSet
from engine.actions.resolver import (
    AmbiguousResolutionError,
    EntityResolver,
    InvalidOrdinalError,
    UnresolvedMentionError,
)
from llm.contracts.action import EntityMention


@pytest.fixture
def candidates() -> CandidateSet:
    return CandidateSet(
        [
            Candidate("obj-1", "object", "Wooden Crate"),
            Candidate("npc-1", "npc", "Bob the Guard"),
            Candidate("npc-2", "npc", "Bob the Merchant"),
            Candidate("item-1", "item", "Crowbar"),
        ]
    )


def test_resolve_exact_ordinal(candidates: CandidateSet) -> None:
    resolver = EntityResolver()
    mention = EntityMention(text="Wooden Crate", role="target", candidate_ordinal=1)
    result = resolver.resolve_mention(mention, candidates)
    assert result.id == "obj-1"


def test_resolve_ordinal_out_of_bounds(candidates: CandidateSet) -> None:
    resolver = EntityResolver()
    mention = EntityMention(text="Wooden Crate", role="target", candidate_ordinal=99)
    with pytest.raises(InvalidOrdinalError, match="out of bounds"):
        resolver.resolve_mention(mention, candidates)


def test_resolve_ordinal_text_mismatch(candidates: CandidateSet) -> None:
    resolver = EntityResolver()
    mention = EntityMention(text="Crowbar", role="target", candidate_ordinal=1)
    with pytest.raises(InvalidOrdinalError, match="Text mismatch"):
        resolver.resolve_mention(mention, candidates)


def test_resolve_text_exact_match(candidates: CandidateSet) -> None:
    resolver = EntityResolver()
    mention = EntityMention(text="Crowbar", role="tool")
    result = resolver.resolve_mention(mention, candidates)
    assert result.id == "item-1"


def test_resolve_text_substring_match(candidates: CandidateSet) -> None:
    resolver = EntityResolver()
    mention = EntityMention(text="Crate", role="target")
    result = resolver.resolve_mention(mention, candidates)
    assert result.id == "obj-1"


def test_resolve_text_not_found(candidates: CandidateSet) -> None:
    resolver = EntityResolver()
    mention = EntityMention(text="Dragon", role="target")
    with pytest.raises(UnresolvedMentionError, match="No candidate found"):
        resolver.resolve_mention(mention, candidates)


def test_resolve_ambiguous_text(candidates: CandidateSet) -> None:
    resolver = EntityResolver()
    mention = EntityMention(text="Bob", role="target")
    with pytest.raises(AmbiguousResolutionError, match="Ambiguous mention"):
        resolver.resolve_mention(mention, candidates)


def test_malicious_arbitrary_id_ignored(candidates: CandidateSet) -> None:
    # LLM cannot pass an arbitrary ID, it can only pass text or ordinal.
    # The Mention struct enforces this, and the resolver only uses CandidateSet.
    # A string resembling an ID passed as text does not match unless it's the actual name.
    resolver = EntityResolver()
    mention = EntityMention(text="obj-999", role="target")
    with pytest.raises(UnresolvedMentionError):
        resolver.resolve_mention(mention, candidates)
