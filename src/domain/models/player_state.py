"""Player runtime state models."""

from pydantic import Field, model_validator

from domain.models.character import StatBlock
from domain.models.common import DisplayString, EntityId, FrozenModel
from domain.models.runtime_common import (
    FusionRecord,
    InventoryEntry,
    KnownCombatSkill,
    ResourceValue,
    StatusInstance,
)


class PlayerState(FrozenModel):
    """The runtime state of the protagonist."""

    id: EntityId
    name: DisplayString
    background_id: EntityId
    stats: StatBlock
    level: int = Field(default=1, ge=1)
    xp: int = Field(default=0, ge=0)
    
    hp: ResourceValue
    armour: ResourceValue
    mana: ResourceValue
    mana_regen: int = Field(ge=0)
    speed: int = Field(ge=0)
    
    luck_current: int = Field(default=0, ge=0)
    luck_capacity: int = Field(ge=0)
    
    inventory: list[InventoryEntry] = Field(default_factory=list)
    equipment: list[InventoryEntry] = Field(default_factory=list)
    
    non_combat_skill_ranks: dict[EntityId, int] = Field(default_factory=dict)
    known_combat_skills: list[KnownCombatSkill] = Field(default_factory=list)
    combat_loadout: list[EntityId] = Field(default_factory=list)
    
    upgrade_tokens: int = Field(default=0, ge=0)
    fusion_history: list[FusionRecord] = Field(default_factory=list)
    statuses: list[StatusInstance] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_invariants(self) -> "PlayerState":
        """Check complex invariants for the player state."""
        # 1. Luck bounds
        if self.luck_current > self.luck_capacity:
            raise ValueError(f"luck_current ({self.luck_current}) cannot exceed luck_capacity ({self.luck_capacity})")
            
        # 2. Non-combat skill ranks bounds
        for skill_id, rank in self.non_combat_skill_ranks.items():
            if not (0 <= rank <= 5):
                raise ValueError(f"non_combat_skill_ranks for {skill_id} must be between 0 and 5, got {rank}")
                
        # 3. Known combat skills must have unique IDs
        known_skill_ids = [k.skill_id for k in self.known_combat_skills]
        if len(known_skill_ids) != len(set(known_skill_ids)):
            raise ValueError("known_combat_skills contains duplicate skill_ids")
            
        known_set = set(known_skill_ids)
            
        # 4. Loadout invariants: distinct, known, max 4
        if len(self.combat_loadout) > 4:
            raise ValueError(f"combat_loadout cannot exceed 4 items, got {len(self.combat_loadout)}")
            
        if len(self.combat_loadout) != len(set(self.combat_loadout)):
            raise ValueError("combat_loadout contains duplicate skill_ids")
            
        for skill_id in self.combat_loadout:
            if skill_id not in known_set:
                raise ValueError(f"combat_loadout contains unknown skill_id {skill_id}")
                
        # 5. Inventory and equipment item uniqueness check
        inv_item_ids = [entry.item_id for entry in self.inventory]
        if len(inv_item_ids) != len(set(inv_item_ids)):
            # Note: the schema says "positive quantity and instance data only for unique items", 
            # so standard items should just have >1 quantity, not multiple entries.
            raise ValueError("inventory contains duplicate item_ids; use quantity instead")
            
        equip_item_ids = [entry.item_id for entry in self.equipment]
        if len(equip_item_ids) != len(set(equip_item_ids)):
            raise ValueError("equipment contains duplicate item_ids")
            
        # Equipment must be a subset of inventory (we check if item exists and quantity >= equipped)
        # However, to avoid complex nested checks and allow items directly equipped, we verify that 
        # an equipped item is tracked *somehow*. The schema says "Equipment references owned entries."
        # This implies it should be in inventory, or equipment is a separate owned list. We'll enforce 
        # it as: if it's in equipment, it is "owned". Wait, the schema says: 
        # "Equipment references owned entries."
        # We can enforce that all equipped item IDs must appear in inventory.
        inv_set = set(inv_item_ids)
        for item_id in equip_item_ids:
            if item_id not in inv_set:
                raise ValueError(f"equipped item_id {item_id} is not in inventory")
                
        # Verify equipped quantity does not exceed inventory quantity
        inv_quantities = {entry.item_id: entry.quantity for entry in self.inventory}
        for entry in self.equipment:
            if entry.quantity > inv_quantities[entry.item_id]:
                raise ValueError(f"equipped quantity of {entry.item_id} exceeds inventory quantity")

        return self
