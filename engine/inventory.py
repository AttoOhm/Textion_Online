"""
Inventory Engine (Phase 6A)

Supports inventory entries with instance IDs.
Do not store raw item IDs directly.

This module provides:
- Inventory management
- Item stacking
- Inventory queries
"""

import uuid
import time
from typing import Optional, Dict, List, Any

# ============ CONSTANTS ============

EVENT_ITEM_ADDED = "item_added"
EVENT_ITEM_REMOVED = "item_removed"

# ============ INVENTORY ENTRY ============


def create_inventory_entry(
    item_id: str,
    quantity: int = 1,
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a canonical inventory entry."""
    if instance_id is None:
        instance_id = "item_" + str(uuid.uuid4())[:8]
    return {
        "instance_id": instance_id,
        "item_id": item_id,
        "quantity": quantity,
    }


def validate_inventory_entry(entry: Dict[str, Any]) -> List[str]:
    """Validate an inventory entry. Returns list of errors (empty = valid)."""
    errors = []
    required = ["instance_id", "item_id", "quantity"]
    for field in required:
        if field not in entry:
            errors.append(f"Missing required field: {field}")
    if entry.get("quantity", 0) < 1:
        errors.append("Quantity must be at least 1")
    return errors


# ============ INVENTORY ENGINE ============


class InventoryEngine:
    """Runtime inventory storage and management."""

    def __init__(self):
        self._inventories: Dict[str, List[Dict[str, Any]]] = {}
        self._events: List[Dict[str, Any]] = []

    def add_item(
        self,
        actor_id: str,
        item_id: str,
        quantity: int = 1,
        current_tick: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Add an item to an actor's inventory.
        
        For stackable items, adds to existing stacks up to max_stack,
        then creates new stacks as needed.
        """
        from engine.items import item_exists, is_stackable, get_max_stack
        if not item_exists(item_id):
            return None

        if actor_id not in self._inventories:
            self._inventories[actor_id] = []

        remaining = quantity
        
        # First, try to add to existing stacks
        if is_stackable(item_id):
            for entry in self._inventories[actor_id]:
                if entry["item_id"] == item_id:
                    max_stack = get_max_stack(item_id)
                    space_in_stack = max_stack - entry["quantity"]
                    if space_in_stack > 0:
                        add_amount = min(remaining, space_in_stack)
                        entry["quantity"] += add_amount
                        remaining -= add_amount
                        if remaining <= 0:
                            self._generate_event(EVENT_ITEM_ADDED, actor_id, item_id, quantity, current_tick)
                            return entry
        
        # Create new stacks for remaining items
        while remaining > 0:
            max_stack = get_max_stack(item_id)
            stack_size = min(remaining, max_stack)
            entry = create_inventory_entry(item_id=item_id, quantity=stack_size)
            self._inventories[actor_id].append(entry)
            remaining -= stack_size
        
        self._generate_event(EVENT_ITEM_ADDED, actor_id, item_id, quantity, current_tick)
        return self._inventories[actor_id][-1]

    def add_item_with_quality(
        self,
        actor_id: str,
        item_id: str,
        quantity: int = 1,
        current_tick: int = 0,
        quality: str = "junior",
        durability_modifier: float = 1.0,
    ) -> Optional[Dict[str, Any]]:
        """Add a crafted item with quality and durability modifiers.
        
        Args:
            actor_id: Actor receiving the item
            item_id: Item identifier
            quantity: Number of items to add
            current_tick: Current world tick
            quality: Quality tier ("junior", "journeyman", "senior", "master")
            durability_modifier: Durability multiplier (0.90, 1.00, 1.10, 1.25)
            
        Returns:
            Created inventory entry with quality data, or None if item doesn't exist
        """
        from engine.items import item_exists, is_stackable
        if not item_exists(item_id):
            return None

        if actor_id not in self._inventories:
            self._inventories[actor_id] = []

        # Get base item data
        from engine.items import get_item_definition
        base_item = get_item_definition(item_id)
        if not base_item:
            return None

        # Calculate modified durability
        base_durability = base_item.get("durability", 100)
        base_max_durability = base_item.get("max_durability", 100)
        
        modified_max_durability = int(base_max_durability * durability_modifier)
        modified_durability = modified_max_durability

        # Create entry with quality data
        entry = create_inventory_entry(item_id=item_id, quantity=quantity)
        entry["quality"] = quality
        entry["durability"] = modified_durability
        entry["max_durability"] = modified_max_durability
        entry["crafted_by"] = actor_id

        # Quality items are unique (not stackable)
        # Always create new entry for quality items
        self._inventories[actor_id].append(entry)
        self._generate_event(EVENT_ITEM_ADDED, actor_id, item_id, quantity, current_tick)
        return entry

    def remove_item(
        self,
        actor_id: str,
        item_id: str,
        quantity: int = 1,
        current_tick: int = 0,
    ) -> bool:
        """Remove an item from an actor's inventory."""
        if actor_id not in self._inventories:
            return False

        for entry in self._inventories[actor_id]:
            if entry["item_id"] == item_id:
                if entry["quantity"] > quantity:
                    entry["quantity"] -= quantity
                    self._generate_event(EVENT_ITEM_REMOVED, actor_id, item_id, quantity, current_tick)
                    return True
                elif entry["quantity"] == quantity:
                    self._inventories[actor_id].remove(entry)
                    self._generate_event(EVENT_ITEM_REMOVED, actor_id, item_id, quantity, current_tick)
                    return True
                else:
                    return False
        return False

    def has_item(self, actor_id: str, item_id: str, quantity: int = 1) -> bool:
        """Check if an actor has an item."""
        if actor_id not in self._inventories:
            return False
        for entry in self._inventories[actor_id]:
            if entry["item_id"] == item_id:
                return entry["quantity"] >= quantity
        return False

    def count_item(self, actor_id: str, item_id: str) -> int:
        """Count how many of an item an actor has."""
        if actor_id not in self._inventories:
            return 0
        for entry in self._inventories[actor_id]:
            if entry["item_id"] == item_id:
                return entry["quantity"]
        return 0

    def get_inventory(self, actor_id: str) -> List[Dict[str, Any]]:
        """Get all items in an actor's inventory."""
        return list(self._inventories.get(actor_id, []))

    def get_entry_by_instance(self, actor_id: str, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get an inventory entry by instance ID."""
        if actor_id not in self._inventories:
            return None
        for entry in self._inventories[actor_id]:
            if entry["instance_id"] == instance_id:
                return entry
        return None

    def get_entry_by_item_id(self, actor_id: str, item_id: str) -> Optional[Dict[str, Any]]:
        """Get an inventory entry by item ID."""
        if actor_id not in self._inventories:
            return None
        for entry in self._inventories[actor_id]:
            if entry["item_id"] == item_id:
                return entry
        return None

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all generated events."""
        return list(self._events)

    def clear_events(self):
        """Clear all events."""
        self._events.clear()

    def _generate_event(self, event_type: str, actor_id: str, item_id: str, quantity: int, tick: int):
        """Generate an event for an inventory change."""
        event = {
            "event_type": event_type,
            "actor_id": actor_id,
            "item_id": item_id,
            "quantity": quantity,
            "tick": tick,
            "timestamp": time.time(),
        }
        self._events.append(event)