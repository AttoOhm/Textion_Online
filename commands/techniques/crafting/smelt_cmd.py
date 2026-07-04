"""
Smelt Command (Phase 7C)

Short command: smelt <resource>
Smelt ores into ingots.

Requires:
- Smelting technique known
- Furnace station in current node
- Input resources in inventory

Creates 1d6 tick Long Action.
No resolution. No skill checks. Deterministic.

At completion:
- Input ores removed from inventory
- Output ingot added to inventory
- No familiarity gained
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.items import get_item_name
import random


# Smelting resources - Primary and Secondary metals
SMELTING_RESOURCES = {
    # Primary metals (basic smelting)
    "copper_ore": {"output": "copper_ingot", "quantity": 8},
    "iron_ore": {"output": "iron_ingot", "quantity": 8},
    "mithril_ore": {"output": "mithril_ingot", "quantity": 8},

}



# Required station
REQUIRED_STATION = "furnace"

# Required technique
REQUIRED_TECHNIQUE = "smelting"

# Duration: 1d6 ticks
MIN_DURATION = 1
MAX_DURATION = 6


def handle_smelt(player_state, resource_name, map_id, node_id,
                 resource_node_manager, inventory_engine, equipment_engine,
                 disciplines_engine, long_action_queue, actor_id, current_tick=0):
    """Handle the 'smelt <resource>' command.

    Args:
        player_state: Player state dict
        resource_name: Name of resource to smelt (e.g., "iron ore" or "bronze ingot")
        map_id: Current map ID
        node_id: Current node ID
        resource_node_manager: ResourceNodeManager instance
        inventory_engine: InventoryEngine instance
        equipment_engine: EquipmentEngine instance
        disciplines_engine: DisciplinesEngine instance
        long_action_queue: ActionQueue instance
        current_tick: Current world tick

    Returns:
        Dict with command result
    """
    
    # Normalize resource name
    resource_name_lower = resource_name.lower().replace(" ", "_")
    
    # Check if this is a basic smeltable resource
    if resource_name_lower in SMELTING_RESOURCES:
        recipe = SMELTING_RESOURCES[resource_name_lower]
        output_item = recipe["output"]
        input_quantity = recipe["quantity"]
        input_item = resource_name_lower
    # Check if this is an advanced alloy recipe
    elif resource_name_lower in ADVANCED_SMELTING:
        recipe = ADVANCED_SMELTING[resource_name_lower]
        output_item = recipe["output"]
        input_quantity = None
        input_item = None  # Multiple inputs
    else:
        return {
            "success": False,
            "message": f"You cannot smelt '{resource_name}'.",
        }
    
    # Check if station exists in current node
    from engine.crafting import create_station
    # We need to check if a furnace station exists in this node
    # This assumes stations are tracked somewhere - for now, we'll check world_items
    # In a full implementation, stations would be in world_items or a station manager
    
    # Check if actor has required technique (from player_state, not technique_manager)
    actor_techniques = player_state.get('techniques', {})
    if REQUIRED_TECHNIQUE not in actor_techniques:
        return {
            "success": False,
            "message": f"You need to know the {REQUIRED_TECHNIQUE} technique.",
        }
    
    # Check if actor has required input resources
    if input_item:  # Basic smelting (single input)
        if not inventory_engine.has_item(actor_id, input_item, input_quantity):
            return {
                "success": False,
                "message": f"You need {input_quantity} {resource_name} to smelt.",
            }
    else:  # Advanced smelting (multiple inputs)
        for ingredient in recipe["inputs"]:
            ing_item = ingredient["item"]
            ing_qty = ingredient["quantity"]
            if not inventory_engine.has_item(actor_id, ing_item, ing_qty):
                return {
                    "success": False,
                    "message": f"You need {ing_qty} {ing_item} to smelt {resource_name}.",
                }
    
    # Check if actor already has active action
    existing_action = long_action_queue.get_actor_action(actor_id)
    if existing_action and existing_action["status"] in ("queued", "active"):
        return {
            "success": False,
            "message": "You are already performing an action.",
        }
    
    # Roll duration: 1d6 ticks
    duration = random.randint(MIN_DURATION, MAX_DURATION)
    
    # Create refinement Long Action
    action = long_action_queue.queue_action(
        actor_id=actor_id,
        action_type="smelt",
        duration_ticks=duration,
        current_tick=current_tick,
        parameters={
            "input_item": input_item,
            "input_quantity": input_quantity,
            "output_item": output_item,
            "technique": REQUIRED_TECHNIQUE,
            "station_type": REQUIRED_STATION,
            "advanced": input_item is None,  # Flag for advanced recipe
            "ingredients": recipe.get("inputs", []),  # For advanced recipes
        },
        resolution_config={},  # No resolution - deterministic
    )
    
    if not action:
        return {
            "success": False,
            "message": "Cannot start smelting action.",
        }
    
    return {
        "success": True,
        "message": f"You begin smelting {resource_name}...",
        "action_id": action["action_id"],
        "end_tick": action["end_tick"],
        "duration": duration,
    }


def complete_smelt(action, inventory_engine, current_tick=0):
    """Complete a smelting action.

    Args:
        action: Completed long action dict
        inventory_engine: InventoryEngine instance
        current_tick: Current world tick

    Returns:
        Dict with completion result
    """
    actor_id = action["actor_id"]
    params = action["parameters"]
    
    input_item = params["input_item"]
    input_quantity = params["input_quantity"]
    output_item = params["output_item"]
    is_advanced = params.get("advanced", False)
    ingredients = params.get("ingredients", [])
    
    # Remove input resources
    if is_advanced and ingredients:
        # Advanced smelting: remove multiple ingredients
        for ingredient in ingredients:
            inventory_engine.remove_item(actor_id, ingredient["item"], ingredient["quantity"], current_tick)
        input_desc = " and ".join([f"{i['quantity']} {i['item']}" for i in ingredients])
    else:
        # Basic smelting: remove single input
        inventory_engine.remove_item(actor_id, input_item, input_quantity, current_tick)
        input_desc = input_item
    
    # Add output item
    inventory_engine.add_item(actor_id, output_item, 1, current_tick)
    
    return {
        "success": True,
        "message": f"You smelt {input_desc} and obtain {get_item_name(output_item)}.",
    }
