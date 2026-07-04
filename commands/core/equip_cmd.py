"""
Equip Command (Phase 6A)

Short command: equip <item>
Equip item.

No long action. No tick cost. No action resolution.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.items import get_item_name


def handle_equip(player_state, item_name, inventory_engine, equipment_engine, current_tick=0):
    """Handle the 'equip <item>' command.

    Args:
        player_state: Player state dict
        item_name: Name of the item to equip
        inventory_engine: InventoryEngine instance
        equipment_engine: EquipmentEngine instance
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

    # Get currently equipped items for smart slot selection
    equipped_items = equipment_engine.get_all_equipped(actor_id)
    
    # Determine slot with smart selection for jewelry
    from engine.equipment import get_slot_for_item
    slot = get_slot_for_item(entry["item_id"], equipped_items)
    
    # Equip the item
    result = equipment_engine.equip_item(
        actor_id=actor_id,
        inventory_entry=entry,
        slot=slot,
        current_tick=current_tick,
    )

    if not result:
        return {
            "success": False,
            "message": f"Failed to equip {item_name}.",
        }

    # Remove from inventory
    inventory_engine.remove_item(actor_id, entry["item_id"], 1, current_tick)

    name = get_item_name(entry["item_id"])
    return {
        "success": True,
        "message": f"You equip the {name}.",
    }