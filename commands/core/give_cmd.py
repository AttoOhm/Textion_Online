"""
Give Command (Phase 6B)

Short command: give <item> to <actor>
Give item from inventory to another actor.

No long action. No tick cost. No action resolution.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.items import get_item_name


def handle_give(player_state, item_name, target_actor_id, inventory_engine, current_tick=0):
    """Handle the 'give <item> to <actor>' command.

    Args:
        player_state: Player state dict
        item_name: Name of the item to give
        target_actor_id: Target actor ID
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

    # Remove from player inventory
    inventory_engine.remove_item(actor_id, entry["item_id"], 1, current_tick)

    # Add to target inventory
    inventory_engine.add_item(target_actor_id, entry["item_id"], 1, current_tick)

    # Generate event
    inventory_engine._generate_event("item_given", actor_id, entry["item_id"], 1, current_tick)

    name = get_item_name(entry["item_id"])
    return {
        "success": True,
        "message": f"You give the {name} to {target_actor_id}.",
    }