"""
Drop Command (Phase 6B)

Short command: drop <item>
Drop item from inventory to current node.

No long action. No tick cost. No action resolution.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.items import get_item_name


def handle_drop(player_state, item_name, map_id, node_id, world_items_engine, inventory_engine, current_tick=0):
    """Handle the 'drop <item>' command.

    Args:
        player_state: Player state dict
        item_name: Name of the item to drop
        map_id: Current map ID
        node_id: Current node ID
        world_items_engine: WorldItemsEngine instance
        inventory_engine: InventoryEngine instance
        current_tick: Current world tick

    Returns:
        Dict with command result
    """
    actor_id = player_state.get("id", "player")

    # Find item in inventory
    inventory = inventory_engine.get_inventory(actor_id)
    entry = None
    for inv_entry in inventory:
        name = get_item_name(inv_entry["item_id"])
        if name.lower() == item_name.lower():
            entry = inv_entry
            break

    if not entry:
        return {
            "success": False,
            "message": f"You don't have '{item_name}' in your inventory.",
        }

    # Remove from inventory
    inventory_engine.remove_item(actor_id, entry["item_id"], 1, current_tick)

    # Add to world
    world_item = world_items_engine.add_world_item(
        item_id=entry["item_id"],
        map_id=map_id,
        node_id=node_id,
        current_tick=current_tick,
    )

    # Generate event
    world_items_engine._generate_event("item_dropped", actor_id, entry["item_id"], current_tick)

    name = get_item_name(entry["item_id"])
    return {
        "success": True,
        "message": f"You drop the {name}.",
    }