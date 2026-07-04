"""
Unequip Command (Phase 6A)

Short command: unequip <item>
Unequip item.

No long action. No tick cost. No action resolution.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.items import get_item_name
from engine.equipment import VALID_SLOTS


def handle_unequip(player_state, item_name, inventory_engine, equipment_engine, current_tick=0):
    """Handle the 'unequip <item>' command.

    Args:
        player_state: Player state dict
        item_name: Name of the item to unequip
        inventory_engine: InventoryEngine instance
        equipment_engine: EquipmentEngine instance
        current_tick: Current world tick

    Returns:
        Dict with command result
    """
    actor_id = player_state.get("id", "player")

    # Find item in equipment by name
    equipped = equipment_engine.get_all_equipped(actor_id)
    slot = None
    entry = None

    for s, e in equipped.items():
        if e:
            name = get_item_name(e["item_id"])
            if name.lower() == item_name.lower():
                slot = s
                entry = e
                break

    if not entry:
        return {
            "success": False,
            "message": f"You don't have '{item_name}' equipped.",
        }

    # Unequip the item
    result = equipment_engine.unequip_item(
        actor_id=actor_id,
        slot=slot,
        current_tick=current_tick,
    )

    if not result:
        return {
            "success": False,
            "message": f"Failed to unequip {item_name}.",
        }

    # Add back to inventory
    inventory_engine.add_item(actor_id, entry["item_id"], 1, current_tick)

    name = get_item_name(entry["item_id"])
    return {
        "success": True,
        "message": f"You unequip the {name}.",
    }