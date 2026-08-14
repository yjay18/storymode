"""Standard exploration operations validation."""

from domain.models.party_state import LifeState
from domain.models.runtime_state import RuntimeState
from engine.actions.candidates import Candidate


class OperationValidationError(Exception):
    """Raised when an operation violates a mechanical rule."""

    pass


class OperationValidator:
    """Validates standard operations against the runtime state and resolved candidates."""

    def validate(
        self, operation: str, resolved_candidates: list[Candidate], state: RuntimeState
    ) -> None:
        """Validate a standard exploration operation."""
        # Simple dispatch for standard ops
        if operation == "travel":
            self._validate_travel(resolved_candidates, state)
        elif operation == "talk":
            self._validate_talk(resolved_candidates, state)
        elif operation == "use_item":
            self._validate_use_item(resolved_candidates, state)
        elif operation in ("investigate", "inspect", "search"):
            self._validate_investigate(resolved_candidates, state)

    def _validate_travel(self, candidates: list[Candidate], state: RuntimeState) -> None:
        if not candidates:
            raise OperationValidationError("Travel requires a destination area")
        target = candidates[0]
        if target.type != "area":
            raise OperationValidationError(f"Cannot travel to a {target.type}, must be an area")

        # Candidates passed in were built from connected areas or visible entities

    def _validate_talk(self, candidates: list[Candidate], state: RuntimeState) -> None:
        if not candidates:
            raise OperationValidationError("Talk requires a target entity")
        target = candidates[0]
        if target.type not in ("npc", "companion"):
            raise OperationValidationError(f"Cannot talk to a {target.type}")

        # Check if the target is dead (via state overrides or companion state)
        if target.type == "companion":
            comp = state.party.companions.get(target.id)
            if comp and comp.life_state == LifeState.DEAD:
                raise OperationValidationError(f"{target.name} is dead and cannot be spoken to")
        elif target.type == "npc":
            override = state.npc_overrides.get(target.id)
            if override and override.life_state == LifeState.DEAD:
                raise OperationValidationError(f"{target.name} is dead and cannot be spoken to")

    def _validate_use_item(self, candidates: list[Candidate], state: RuntimeState) -> None:
        # Require at least one item
        items = [c for c in candidates if c.type == "item"]
        if not items:
            raise OperationValidationError("Use item requires an item candidate")

        # Ensure the item is in inventory
        for item in items:
            found = False
            for inv_entry in state.player.inventory:
                if inv_entry.item_id == item.id:
                    found = True
                    break
            if not found:
                raise OperationValidationError(f"You do not have {item.name}")

    def _validate_investigate(self, candidates: list[Candidate], state: RuntimeState) -> None:
        # Candidates must be reachable/visible (assumed by CandidateSet building)
        for c in candidates:
            if c.type == "area":
                raise OperationValidationError(
                    "Cannot investigate an entire connected area from afar"
                )
