"""
Grind Command (Phase 7C)

Short command: grind <resource>
Grind berries into mash.

Requires:
- Preserving technique known
- Mortar station in current node
- Input berries in inventory

Creates 1d6 tick Long Action.
No resolution. No skill checks. Deterministic.

At completion:
- Input berries removed from inventory
- Output mash added to inventory
- No familiarity gained
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.items import get_item_name
import random


# Preserving resources - Primary and Secondary food materials
PRESERVING_RESOURCES = {
    # Primary food materials
    "green_berry": {"output": "green_mash", "quantity": 8},
    "red_berry": {"output": "red_mash", "quantity": 8},
    "black_berry": {"output": "black_mash", "quantity": 8},
    # Secondary food materials (grains)
    "wheat": {"output": "wheat", "quantity": 8},
    "rice": {"output": "rice", "quantity": 8},
    "barley": {"output": "barley", "quantity": 8},
}

# Advanced preserving (mixed mash) - requires two input types
ADVANCED_PRESERVING = {
    "yellow_mash": {
        "inputs": [
            {"item": "green_berry", "quantity": 8},
            {"item": "wheat", "quantity": 8},
        ],
        "output": "yellow_mash",
    },
    "pink_mash": {
        "inputs": [
            {"item": "red_berry", "quantity": 8},
            {"item": "rice", "quantity": 8},
        ],
        "output": "pink_mash",
    },
    "purple_mash": {
        "inputs": [
            {"item": "black_berry", "quantity": 8},
            {"item": "barley", "quantity": 8},
        ],
        "output": "purple_mash",
    },
}

# Required station
REQUIRED_STATION = "mortar"

# Required technique
REQUIRED_TECHNIQUE = "preserving"

# Duration: 1d5 ticks
MIN_DURATION = 1
MAX_DURATION = 6

def handle_grind(player_state, resource_name, map_id, node_id,
                 resource_node_manager, inventory_engine, equipment_engine,
                 disciplines_engine, long_action_queue, current_tick=0):
    """Handle the 'grind <resource>' command.

    Args:
        player_state: Player state dict
        resource_name: Name of resource to grind (e.g., "green berry" or "yellow mash")
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
    actor_id = player_state.get("id", "player")
    
    # Normalize resource name
    resource_name_lower = resource_name.lower().replace(" ", "_")
    
    # Check if this is a basic grindable resource
    if resource_name_lower in PRESERVING_RESOURCES:
        recipe = PRESERVING_RESOURCES[resource_name_lower]
        output_item = recipe["output"]
        input_quantity = recipe["quantity"]
        input_item = resource_name_lower
    # Check if this is an advanced mixed mash recipe
    elif resource_name_lower in ADVANCED_PRESERVING:
        recipe = ADVANCED_PRESERVING[resource_name_lower]
        output_item = recipe["output"]
        input_quantity = None
        input_item = None  # Multiple inputs
    else:
        return {
            "success": False,
            "message": f"You cannot grind '{resource_name}'.",
        }
    
    # Check if actor has required technique
    if not disciplines_engine.has_technique(actor_id, REQUIRED_TECHNIQUE):
        return {
            "success": False,
            "message": f"You need to know the {REQUIRED_TECHNIQUE} technique.",
        }
    
    # Check if actor has required input resources
    if input_item:  # Basic preserving (single input)
        if not inventory_engine.has_item(actor_id, input_item, input_quantity):
            return {
                "success": False,
                "message": f"You need {input_quantity} {resource_name} to grind.",
            }
    else:  # Advanced preserving (multiple inputs)
        for ingredient in recipe["inputs"]:
            ing_item = ingredient["item"]
            ing_qty = ingredient["quantity"]
            if not inventory_engine.has_item(actor_id, ing_item, ing_qty):
                return {
                    "success": False,
                    "message": f"You need {ing_qty} {ing_item} to grind {resource_name}.",
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
        action_type="grind",
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
            "message": "Cannot start grinding action.",
        }
    
    return {
        "success": True,
        "message": f"You begin grinding {resource_name}...",
        "action_id": action["action_id"],
        "end_tick": action["end_tick"],
        "duration": duration,
    }


def complete_grind(action, inventory_engine, current_tick=0):
    """Complete a grinding action.

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
        # Advanced preserving: remove multiple ingredients
        for ingredient in ingredients:
            inventory_engine.remove_item(actor_id, ingredient["item"], ingredient["quantity"], current_tick)
        input_desc = " and ".join([f"{i['quantity']} {i['item']}" for i in ingredients])
    else:
        # Basic preserving: remove single input
        inventory_engine.remove_item(actor_id, input_item, input_quantity, current_tick)
        input_desc = input_item
    
    # Add output item
    inventory_engine.add_item(actor_id, output_item, 1, current_tick)
    
    return {
        "success": True,
        "message": f"You grind {input_desc} and obtain {get_item_name(output_item)}.",
    }
