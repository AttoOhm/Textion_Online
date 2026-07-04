"""
Inventory Command (Phase 6A)

Short command: inventory
Displays inventory contents.

No long action. No tick cost. No action resolution.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.items import get_item_name, get_item_type


def handle_inventory(player_state, inventory_engine):
    """Handle the 'inventory' command.

    Args:
        player_state: Player state dict
        inventory_engine: InventoryEngine instance

    Returns:
        Dict with command result
    """
    actor_id = player_state.get("id", "player")
    inventory = inventory_engine.get_inventory(actor_id)

    if not inventory:
        return {
            "success": True,
            "message": "Your inventory is empty.",
            "items": []
        }

    items = []
    for entry in inventory:
        item_id = entry["item_id"]
        quantity = entry["quantity"]
        name = get_item_name(item_id)
        item_type = get_item_type(item_id)

        items.append({
            "instance_id": entry["instance_id"],
            "item_id": item_id,
            "name": name,
            "type": item_type,
            "quantity": quantity,
        })

    # Build message
    lines = ["Your inventory:"]
    for item in items:
        if item["quantity"] > 1:
            lines.append(f"  {item['name']} x{item['quantity']}")
        else:
            lines.append(f"  {item['name']}")

    return {
        "success": True,
        "message": "\n".join(lines),
        "items": items,
    }