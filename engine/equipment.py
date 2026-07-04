"""
Equipment Engine (Phase 6A)

Supports equipment slots and item equipping.
Equipment references inventory entries, not item definitions.

This module provides:
- Equipment management
- Slot validation
- Equipment queries
"""

import time
from typing import Optional, Dict, List, Any

# ============ CONSTANTS ============

# Equipment slots (frozen design)
VALID_SLOTS = [
    "main_hand",
    "off_hand",
    "armor",
    "necklace_1",
    "necklace_2",
    "bracelet_1",
    "bracelet_2",
    "bracelet_3",
    "bracelet_4",
    "ring_1",
    "ring_2",
    "ring_3",
    "ring_4",
    "ring_5",
    "ring_6",
    "ring_7",
    "ring_8",
]

# Event types
EVENT_ITEM_EQUIPPED = "item_equipped"
EVENT_ITEM_UNEQUIPPED = "item_unequipped"


def get_slot_for_item(item_id: str, equipped_items: Optional[Dict[str, Optional[Dict]]] = None) -> str:
    """Get the appropriate slot for an item type.

    Args:
        item_id: Item identifier
        equipped_items: Dict of currently equipped items (for finding empty slots)

    Returns:
        Slot name
    """
    from engine.items import get_item_type, get_item_subtype

    item_type = get_item_type(item_id)
    subtype = get_item_subtype(item_id)

    if item_type == "weapon":
        if subtype == "shield":
            return "off_hand"
        return "main_hand"
    elif item_type == "armor":
        if subtype == "shield":
            return "off_hand"
        else:
            # All armor (chest, head, legs, feet) goes to single "armor" slot
            return "armor"
    elif item_type == "ammo" and subtype == "quiver":
        # Quivers go in off_hand (container for arrows)
        return "off_hand"
    elif item_type == "jewelry":
        if subtype == "necklace":
            # Return first available necklace slot
            if equipped_items:
                for i in range(1, 3):  # necklace_1, necklace_2
                    slot = f"necklace_{i}"
                    if not equipped_items.get(slot):
                        return slot
            return "necklace_1"
        elif subtype == "bracelet":
            # Return first available bracelet slot
            if equipped_items:
                for i in range(1, 5):  # bracelet_1-4
                    slot = f"bracelet_{i}"
                    if not equipped_items.get(slot):
                        return slot
            return "bracelet_1"
        elif subtype == "ring":
            # Return first available ring slot
            if equipped_items:
                for i in range(1, 9):  # ring_1-8
                    slot = f"ring_{i}"
                    if not equipped_items.get(slot):
                        return slot
            return "ring_1"

    return "main_hand"


def validate_slot(slot: str) -> List[str]:
    """Validate a slot name. Returns list of errors (empty = valid)."""
    errors = []
    if slot not in VALID_SLOTS:
        errors.append(f"Invalid slot: {slot}")
    return errors


# ============ EQUIPMENT ENGINE ============


class EquipmentEngine:
    """Runtime equipment storage and management."""

    def __init__(self):
        self._equipment: Dict[str, Dict[str, Optional[Dict]]] = {}  # actor_id -> {slot: entry}
        self._events: List[Dict[str, Any]] = []

    def equip_item(
        self,
        actor_id: str,
        inventory_entry: Dict[str, Any],
        slot: Optional[str] = None,
        current_tick: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Equip an item from inventory.

        Args:
            actor_id: Actor identifier
            inventory_entry: Inventory entry dict
            slot: Equipment slot (auto-determined if None)
            current_tick: Current world tick

        Returns:
            The equipped item dict, or None if failed
        """
        item_id = inventory_entry.get("item_id", "")

        # Determine slot
        if slot is None:
            slot = get_slot_for_item(item_id)

        # Validate slot
        errors = validate_slot(slot)
        if errors:
            return None

        # Initialize equipment if needed
        if actor_id not in self._equipment:
            self._equipment[actor_id] = {s: None for s in VALID_SLOTS}

        # Store previously equipped item
        previous = self._equipment[actor_id].get(slot)

        # Equip new item
        self._equipment[actor_id][slot] = inventory_entry

        # Generate event
        self._generate_event(EVENT_ITEM_EQUIPPED, actor_id, item_id, slot, current_tick)

        return inventory_entry

    def unequip_item(
        self,
        actor_id: str,
        slot: str,
        current_tick: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Unequip an item from a slot.

        Args:
            actor_id: Actor identifier
            slot: Equipment slot
            current_tick: Current world tick

        Returns:
            The unequipped inventory entry, or None if slot empty
        """
        if actor_id not in self._equipment:
            return None

        entry = self._equipment[actor_id].get(slot)
        if not entry:
            return None

        # Remove from slot
        self._equipment[actor_id][slot] = None

        # Generate event
        self._generate_event(EVENT_ITEM_UNEQUIPPED, actor_id, entry.get("item_id", ""), slot, current_tick)

        return entry

    def get_equipped_item(self, actor_id: str, slot: str) -> Optional[Dict[str, Any]]:
        """Get the item equipped in a slot.

        Args:
            actor_id: Actor identifier
            slot: Equipment slot

        Returns:
            Inventory entry dict or None
        """
        if actor_id not in self._equipment:
            return None
        return self._equipment[actor_id].get(slot)

    def get_all_equipped(self, actor_id: str) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get all equipped items.

        Args:
            actor_id: Actor identifier

        Returns:
            Dict of slot -> inventory entry
        """
        if actor_id not in self._equipment:
            return {s: None for s in VALID_SLOTS}
        return dict(self._equipment[actor_id])

    def has_equipped(self, actor_id: str, item_id: str) -> bool:
        """Check if an actor has a specific item equipped.

        Args:
            actor_id: Actor identifier
            item_id: Item identifier

        Returns:
            True if item is equipped
        """
        if actor_id not in self._equipment:
            return False
        for slot, entry in self._equipment[actor_id].items():
            if entry and entry.get("item_id") == item_id:
                return True
        return False

    def validate_equipment(self, actor_id: str) -> List[str]:
        """Validate equipment for an actor. Returns list of errors."""
        errors = []
        if actor_id not in self._equipment:
            return errors

        for slot, entry in self._equipment[actor_id].items():
            if entry:
                # Validate slot
                slot_errors = validate_slot(slot)
                errors.extend(slot_errors)

                # Validate item exists in inventory
                # (This would check inventory, but we don't have access here)
                # For now, just validate the entry structure
                entry_errors = []
                if "instance_id" not in entry:
                    entry_errors.append(f"Slot {slot}: missing instance_id")
                if "item_id" not in entry:
                    entry_errors.append(f"Slot {slot}: missing item_id")
                errors.extend(entry_errors)

        return errors

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all generated events."""
        return list(self._events)

    def clear_events(self):
        """Clear all events."""
        self._events.clear()

    def _generate_event(self, event_type: str, actor_id: str, item_id: str, slot: str, tick: int):
        """Generate an event for an equipment change."""
        event = {
            "event_type": event_type,
            "actor_id": actor_id,
            "item_id": item_id,
            "slot": slot,
            "tick": tick,
            "timestamp": time.time(),
        }
        self._events.append(event)