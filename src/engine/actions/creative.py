"""Creative capability and object combination validation."""

from domain.models.area import AreaObject
from domain.models.runtime_state import RuntimeState
from engine.actions.candidates import Candidate
from engine.actions.operations import OperationValidationError


class CreativeValidator:
    """Validates creative actions combining capabilities and object states."""
    
    def validate(
        self,
        capability_mentions: list[str],
        resolved_candidates: list[Candidate],
        area_objects: dict[str, AreaObject],
        state: RuntimeState,
    ) -> None:
        """Validate a creative action against object requirements."""
        if not resolved_candidates:
            raise OperationValidationError("Creative action requires at least one target candidate")
            
        target = resolved_candidates[0]
        if target.type != "object":
            raise OperationValidationError(f"Creative interactions require an object target, got {target.type}")
            
        area_obj = area_objects.get(target.id)
        if not area_obj:
            raise OperationValidationError(f"Target object {target.id} not found in area definition")
            
        if not area_obj.capability_requirements:
            # If no capabilities required, it's always valid or handled by standard ops.
            # For creative, we assume it's valid if there are no strict blockers.
            return
            
        # Extract party capabilities: inventory items + non-combat skills
        # This is a simplified capability extraction: we just use the IDs or names of inventory/skills.
        # Ideally, we map `capability_mentions` to real items/skills.
        # But we must ensure that the object's `capability_requirements` are satisfied.
        
        # Build available capability strings (lowercase for matching)
        available_caps = set()
        for item in state.player.inventory:
            available_caps.add(item.item_id.lower())
        for skill_id in state.player.non_combat_skill_ranks:
            available_caps.add(skill_id.lower())
            
        for comp_id in state.party.active_companion_ids:
            comp = state.party.companions.get(comp_id)
            if comp:
                # Add companion skills if applicable, but for now just add companion ID as a capability
                available_caps.add(comp_id.lower())
                
        # Check requirements (require ALL or ANY? usually ANY capability that matches a requirement)
        # Let's say if the object has requirements, the player must possess at least one mentioned capability
        # that satisfies one of the requirements.
        
        # Find which capability mentions match the player's available caps
        valid_mentioned_caps = set()
        for mention in capability_mentions:
            m_lower = mention.lower()
            # If the mention matches an available capability exactly or as a substring
            for cap in available_caps:
                if cap in m_lower or m_lower in cap:
                    valid_mentioned_caps.add(cap)
                    
        # Check if any valid mentioned capability satisfies an object requirement
        satisfied = False
        for req in area_obj.capability_requirements:
            req_lower = req.lower()
            if req_lower in valid_mentioned_caps:
                satisfied = True
                break
                
        if not satisfied:
            req_str = ", ".join(area_obj.capability_requirements)
            raise OperationValidationError(
                f"Creative action rejected: {target.name} requires one of: {req_str}"
            )
