"""Engine-internal structural protocols for action pipeline inputs.

These protocols let the engine package depend on *shapes* rather than concrete
llm-package types, keeping the engine → llm boundary clean.

``llm.contracts.action.ActionProposal`` and ``llm.contracts.action.EntityMention``
structurally satisfy ``ActionProposalLike`` and ``EntityMentionLike`` respectively.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class EntityMentionLike(Protocol):
    """Structural protocol for entity mentions passed to the engine."""

    @property
    def text(self) -> str:
        ...

    @property
    def role(self) -> str:
        ...

    @property
    def candidate_ordinal(self) -> int | None:
        ...


class ActionProposalLike(Protocol):
    """Structural protocol for action proposals passed to the engine.

    ``llm.contracts.action.ActionProposal`` satisfies this protocol at
    call sites.
    """

    @property
    def entity_mentions(self) -> Sequence[EntityMentionLike]:
        ...

    @property
    def capability_mentions(self) -> Sequence[str]:
        ...

    @property
    def operation(self) -> str:
        ...

    @property
    def challenge_label(self) -> str:
        ...

    @property
    def stakes(self) -> Sequence[str]:
        ...

    @property
    def verb(self) -> str:
        ...

    @property
    def intended_effect(self) -> str:
        ...
