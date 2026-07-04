"""
Use Command (Phase 6A)

Short command: use <item>
Use item.

No long action. No tick cost. No action resolution.

Only routing and validation. Future systems will define behavior.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.items import get_item_name, get_item_type


def handle_use(player_state, item_name, inventory_engine, current_tick=0):
    """Handle the 'use <item>' command.

    Args:
        player_state: Player state dict
        item_name: Name of the item to use
        inventory_engine: InventoryEngine instance
        current_tick: Current world tick

    Returns:
        Dict with command result
    """
    actor_id = player_state.get("id", "player")

    # Find item in inventory by name
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

    item_id = entry["item_id"]
    item_type = get_item_type(item_id)
    name = get_item_name(item_id)

    # Placeholder routing based on item type
    # Future systems will define actual behavior
    if item_type == "potion":
        return {
            "success": True,
            "message": f"You drink the {name}. (Effect not yet implemented)",
            "consumed": True,
        }
    elif item_type == "food":
        return {
            "success": True,
            "message": f"You eat the {name}. (Effect not yet implemented)",
            "consumed": True,
        }
    elif item_type == "key":
        return {
            "success": True,
            "message": f"You use the {name}. (Effect not yet implemented)",
            "consumed": False,
        }
    else:
        return {
            "success": False,
            "message": f"You cannot use the {name}.",
        }