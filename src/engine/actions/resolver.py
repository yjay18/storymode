"""Entity resolver."""

from engine.actions.candidates import Candidate, CandidateSet
from engine.actions.protocols import EntityMentionLike


class ResolverError(Exception):
    """Base class for resolver errors."""

    pass


class AmbiguousResolutionError(ResolverError):
    """Raised when a mention is ambiguous."""

    pass


class UnresolvedMentionError(ResolverError):
    """Raised when a mention cannot be resolved."""

    pass


class InvalidOrdinalError(ResolverError):
    """Raised when a mention's ordinal is invalid or incompatible."""

    pass


class EntityResolver:
    """Resolves LLM entity mentions against a bounded CandidateSet."""

    def resolve_mention(self, mention: EntityMentionLike, candidates: CandidateSet) -> Candidate:
        """Resolve a single entity mention."""
        if mention.candidate_ordinal is not None:
            candidate = candidates.get_by_ordinal(mention.candidate_ordinal)
            if not candidate:
                raise InvalidOrdinalError(f"Ordinal {mention.candidate_ordinal} is out of bounds")

            if not self._is_compatible_text(mention.text, candidate.name):
                raise InvalidOrdinalError(
                    f"Text mismatch for ordinal {mention.candidate_ordinal}: "
                    f"'{mention.text}' is not compatible with '{candidate.name}'"
                )
            return candidate

        # Try finding by text
        matches = []
        for c in candidates.candidates:
            if self._is_compatible_text(mention.text, c.name):
                matches.append(c)

        if not matches:
            raise UnresolvedMentionError(f"No candidate found for '{mention.text}'")

        if len(matches) > 1:
            raise AmbiguousResolutionError(
                f"Ambiguous mention '{mention.text}' matches multiple candidates"
            )

        return matches[0]

    def _is_compatible_text(self, text: str, name: str) -> bool:
        """Check if mention text is compatible with the candidate name.

        A simple substring match both ways handles basic LLM truncation or elaboration.
        """
        t = text.lower().strip()
        n = name.lower().strip()
        return t == n or t in n or n in t
