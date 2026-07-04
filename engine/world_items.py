"""
World Items Engine (Phase 6B)

Connects the world to the inventory system.
World items are physical things that exist in nodes.

This module provides:
- World item instance management
- Node item storage
- Container support
"""

import uuid
import time
from typing import Optional, Dict, List, Any

# ============ CONSTANTS ============

EVENT_ITEM_TAKEN = "item_taken"
EVENT_ITEM_DROPPED = "item_dropped"
EVENT_ITEM_STORED = "item_stored"
EVENT_ITEM_REMOVED_FROM_CONTAINER = "item_removed_from_container"


# ============ WORLD ITEM INSTANCE ============


def create_world_item(
    item_id: str,
    map_id: str = "",
    node_id: str = "",
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a canonical world item instance.

    Args:
        item_id: Item definition ID
        map_id: Map where item exists
        node_id: Node where item exists
        instance_id: Unique instance ID (auto-generated if None)

    Returns:
        Dict representing the world item
    """
    if instance_id is None:
        instance_id = "witem_" + str(uuid.uuid4())[:8]

    return {
        "instance_id": instance_id,
        "item_id": item_id,
        "map_id": map_id,
        "node_id": node_id,
    }


def validate_world_item(item: Dict[str, Any]) -> List[str]:
    """Validate a world item instance. Returns list of errors (empty = valid)."""
    errors = []
    required = ["instance_id", "item_id"]
    for field in required:
        if field not in item:
            errors.append(f"Missing required field: {field}")
    return errors


# ============ WORLD ITEMS ENGINE ============


class WorldItemsEngine:
    """Runtime world item storage and management."""

    def __init__(self):
        self._world_items: Dict[str, Dict[str, Any]] = {}  # instance_id -> world item
        self._node_items: Dict[str, List[str]] = {}  # "map_id:node_id" -> [instance_ids]
        self._containers: Dict[str, List[str]] = {}  # container_instance_id -> [item_instance_ids]
        self._events: List[Dict[str, Any]] = []

    def add_world_item(
        self,
        item_id: str,
        map_id: str = "",
        node_id: str = "",
        current_tick: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Add a world item to a node.

        Args:
            item_id: Item definition ID
            map_id: Map where item exists
            node_id: Node where item exists
            current_tick: Current world tick

        Returns:
            The created world item dict
        """
        from engine.items import item_exists
        if not item_exists(item_id):
            return None

        item = create_world_item(item_id=item_id, map_id=map_id, node_id=node_id)
        self._world_items[item["instance_id"]] = item

        # Add to node storage
        node_key = f"{map_id}:{node_id}"
        if node_key not in self._node_items:
            self._node_items[node_key] = []
        self._node_items[node_key].append(item["instance_id"])

        return item

    def remove_world_item(self, instance_id: str, current_tick: int = 0) -> bool:
        """Remove a world item.

        Args:
            instance_id: World item instance ID
            current_tick: Current world tick

        Returns:
            True if removed, False if not found
        """
        item = self._world_items.get(instance_id)
        if not item:
            return False

        # Remove from node storage
        node_key = f"{item.get('map_id', '')}:{item.get('node_id', '')}"
        if node_key in self._node_items:
            if instance_id in self._node_items[node_key]:
                self._node_items[node_key].remove(instance_id)

        # Remove from containers
        for container_id, items in self._containers.items():
            if instance_id in items:
                items.remove(instance_id)

        # Remove from world
        del self._world_items[instance_id]
        return True

    def get_world_item(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get a world item by instance ID.

        Args:
            instance_id: World item instance ID

        Returns:
            World item dict or None
        """
        return self._world_items.get(instance_id)

    def get_node_items(self, map_id: str, node_id: str) -> List[Dict[str, Any]]:
        """Get all items in a node.

        Args:
            map_id: Map ID
            node_id: Node ID

        Returns:
            List of world item dicts
        """
        node_key = f"{map_id}:{node_id}"
        instance_ids = self._node_items.get(node_key, [])
        items = []
        for iid in instance_ids:
            item = self._world_items.get(iid)
            if item:
                items.append(item)
        return items

    def find_world_item(self, item_id: str, map_id: str = "", node_id: str = "") -> Optional[Dict[str, Any]]:
        """Find a world item by item ID.

        Args:
            item_id: Item definition ID
            map_id: Optional map filter
            node_id: Optional node filter

        Returns:
            World item dict or None
        """
        for item in self._world_items.values():
            if item["item_id"] == item_id:
                if map_id and item.get("map_id") != map_id:
                    continue
                if node_id and item.get("node_id") != node_id:
                    continue
                return item
        return None

    def move_world_item(self, instance_id: str, new_map_id: str, new_node_id: str) -> bool:
        """Move a world item to a new location.

        Args:
            instance_id: World item instance ID
            new_map_id: New map ID
            new_node_id: New node ID

        Returns:
            True if moved, False if not found
        """
        item = self._world_items.get(instance_id)
        if not item:
            return False

        # Remove from old node
        old_node_key = f"{item.get('map_id', '')}:{item.get('node_id', '')}"
        if old_node_key in self._node_items:
            if instance_id in self._node_items[old_node_key]:
                self._node_items[old_node_key].remove(instance_id)

        # Update location
        item["map_id"] = new_map_id
        item["node_id"] = new_node_id

        # Add to new node
        new_node_key = f"{new_map_id}:{new_node_id}"
        if new_node_key not in self._node_items:
            self._node_items[new_node_key] = []
        self._node_items[new_node_key].append(instance_id)

        return True

    # ============ CONTAINER SUPPORT ============

    def add_item_to_container(
        self,
        container_id: str,
        item_instance_id: str,
        current_tick: int = 0,
    ) -> bool:
        """Add an item to a container.

        Args:
            container_id: Container instance ID
            item_instance_id: Item instance ID to add
            current_tick: Current world tick

        Returns:
            True if added, False if not found
        """
        item = self._world_items.get(item_instance_id)
        if not item:
            return False

        if container_id not in self._containers:
            self._containers[container_id] = []

        self._containers[container_id].append(item_instance_id)

        # Generate event
        self._generate_event(EVENT_ITEM_STORED, container_id, item.get("item_id", ""), current_tick)

        return True

    def remove_item_from_container(
        self,
        container_id: str,
        item_instance_id: str,
        current_tick: int = 0,
    ) -> bool:
        """Remove an item from a container.

        Args:
            container_id: Container instance ID
            item_instance_id: Item instance ID to remove
            current_tick: Current world tick

        Returns:
            True if removed, False if not found
        """
        if container_id not in self._containers:
            return False

        if item_instance_id not in self._containers[container_id]:
            return False

        self._containers[container_id].remove(item_instance_id)

        # Generate event
        item = self._world_items.get(item_instance_id)
        if item:
            self._generate_event(EVENT_ITEM_REMOVED_FROM_CONTAINER, container_id, item.get("item_id", ""), current_tick)

        return True

    def get_container_items(self, container_id: str) -> List[Dict[str, Any]]:
        """Get all items in a container.

        Args:
            container_id: Container instance ID

        Returns:
            List of world item dicts
        """
        instance_ids = self._containers.get(container_id, [])
        items = []
        for iid in instance_ids:
            item = self._world_items.get(iid)
            if item:
                items.append(item)
        return items

    # ============ EVENTS ============

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all generated events."""
        return list(self._events)

    def clear_events(self):
        """Clear all events."""
        self._events.clear()

    def _generate_event(self, event_type: str, source_id: str, item_id: str, tick: int):
        """Generate an event for a world item change."""
        event = {
            "event_type": event_type,
            "source_id": source_id,
            "item_id": item_id,
            "tick": tick,
            "timestamp": time.time(),
        }
        self._events.append(event)