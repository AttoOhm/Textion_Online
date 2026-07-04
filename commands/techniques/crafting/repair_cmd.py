"""
Repair Command (Phase 7E)

Short command: repair <item>
Repair damaged weapons and tools.

Requires:
- repair_weapon technique known
- workbench station in current node
- Repair materials (25% of original crafting materials)
- Item has durability > 0

Creates 1d6 tick Long Action.
No resolution. No skill checks. Deterministic.

At completion:
- Item durability restored to max
- Repair materials consumed
- No familiarity gained
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.items import get_item_name
import random


# Required station
REQUIRED_STATION = "workbench"

# Required technique
REQUIRED_TECHNIQUE = "repair_weapon"

# Duration: 1d6 ticks
MIN_DURATION = 1
MAX_DURATION = 6

# Repair cost: 25% of original materials (round up)
REPAIR_PERCENTAGE = 0.25


def handle_repair(player_state, item_name, map_id, node_id,
                  resource_node_manager, inventory_engine, equipment_engine,
                  disciplines_engine, recipe_manager, long_action_queue,
                  current_tick=0):
    """Handle the 'repair <item>' command.

    Args:
        player_state: Player state dict
        item_name: Name of item to repair (e.g., "iron sword")
        map_id: Current map ID
        node_id: Current node ID
        resource_node_manager: ResourceNodeManager instance
        inventory_engine: InventoryEngine instance
        equipment_engine: EquipmentEngine instance
        disciplines_engine: DisciplinesEngine instance
        recipe_manager: RecipeManager instance
        long_action_queue: ActionQueue instance
        current_tick: Current world tick

    Returns:
        Dict with command result
    """
    actor_id = player_state.get("id", "player")
    
    # Normalize item name
    item_name_lower = item_name.lower().replace(" ", "_")
    
    # Check if item exists in inventory
    item_data = inventory_engine.get_item(actor_id, item_name_lower)
    if not item_data:
        return {
            "success": False,
            "message": f"You don't have '{item_name}'.",
        }
    
    # Check if item is repairable (has durability)
    if "durability" not in item_data and "max_durability" not in item_data:
        return {
            "success": False,
            "message": f"You cannot repair '{item_name}'.",
        }
    
    current_durability = item_data.get("durability", 0)
    max_durability = item_data.get("max_durability", 0)
    
    # Check if item is already broken
    if current_durability <= 0:
        return {
            "success": False,
            "message": f"'{item_name}' is broken and cannot be repaired.",
        }
    
    # Check if item is already at full durability
    if current_durability >= max_durability:
        return {
            "success": False,
            "message": f"'{item_name}' is already at full durability.",
        }
    
    # Check if actor has required technique
    if not disciplines_engine.has_technique(actor_id, REQUIRED_TECHNIQUE):
        return {
            "success": False,
            "message": f"You need to know the {REQUIRED_TECHNIQUE} technique.",
        }
    
    # Check if required station (workbench) is present
    if not resource_node_manager.has_station_type(map_id, node_id, REQUIRED_STATION):
        return {
            "success": False,
            "message": f"You must be near a {REQUIRED_STATION.replace('_', ' ')} to repair {item_name}.",
        }
    
    # Calculate repair materials (25% of original, round up)
    repair_materials = _calculate_repair_materials(item_name_lower, recipe_manager)
    if not repair_materials:
        return {
            "success": False,
            "message": f"'{item_name}' cannot be repaired (no recipe found).",
        }
    
    # Check if actor has repair materials
    for material in repair_materials:
        mat_item = material["item"]
        mat_qty = material["quantity"]
        if not inventory_engine.has_item(actor_id, mat_item, mat_qty):
            return {
                "success": False,
                "message": f"You need {mat_qty} {mat_item} to repair {item_name}.",
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
    
    # Create repair Long Action
    action = long_action_queue.queue_action(
        actor_id=actor_id,
        action_type="repair",
        duration_ticks=duration,
        current_tick=current_tick,
        parameters={
            "item_id": item_name_lower,
            "item_name": item_name,
            "repair_materials": repair_materials,
            "technique": REQUIRED_TECHNIQUE,
            "station_type": REQUIRED_STATION,
        },
        resolution_config={},  # No resolution - deterministic
    )
    
    if not action:
        return {
            "success": False,
            "message": "Cannot start repair action.",
        }
    
    return {
        "success": True,
        "message": f"You begin repairing {item_name}...",
        "action_id": action["action_id"],
        "end_tick": action["end_tick"],
        "duration": duration,
    }


def complete_repair(action, inventory_engine, equipment_engine, current_tick=0):
    """Complete a repair action.

    Args:
        action: Completed long action dict
        inventory_engine: InventoryEngine instance
        equipment_engine: EquipmentEngine instance
        current_tick: Current world tick

    Returns:
        Dict with completion result
    """
    actor_id = action["actor_id"]
    params = action["parameters"]
    
    item_id = params["item_id"]
    item_name = params["item_name"]
    repair_materials = params["repair_materials"]
    
    # Remove repair materials
    for material in repair_materials:
        mat_item = material["item"]
        mat_qty = material["quantity"]
        inventory_engine.remove_item(actor_id, mat_item, mat_qty, current_tick)
    
    # Restore item durability to max
    item_data = inventory_engine.get_item(actor_id, item_id)
    if item_data:
        max_durability = item_data.get("max_durability", 100)
        inventory_engine.set_item_durability(actor_id, item_id, max_durability, current_tick)
    
    # Build result message
    material_names = ", ".join([m["item"] for m in repair_materials])
    message = f"You repair {item_name} using {material_names}. Durability restored to full."
    
    return {
        "success": True,
        "message": message,
    }


def _calculate_repair_materials(item_id: str, recipe_manager) -> list:
    """Calculate repair materials (25% of original crafting materials, round up).
    
    Args:
        item_id: Item ID to repair
        recipe_manager: RecipeManager instance
        
    Returns:
        List of repair material requirements
    """
    # Try to find the recipe that creates this item
    recipe = recipe_manager.get_recipe_definition(item_id)
    if not recipe:
        return []
    
    # Get original crafting materials
    inputs = recipe.get("inputs", [])
    if not inputs:
        return []
    
    # Calculate 25% of each material (round up)
    repair_materials = []
    for material in inputs:
        mat_item = material["item"]
        mat_qty = material["quantity"]
        repair_qty = max(1, int(mat_qty * REPAIR_PERCENTAGE + 0.5))  # Round up
        
        repair_materials.append({
            "item": mat_item,
            "quantity": repair_qty,
        })
    
    return repair_materials


def _is_repairable_item(item_data: dict) -> bool:
    """Check if an item can be repaired.
    
    Args:
        item_data: Item data dict from inventory
        
    Returns:
        True if item is repairable
    """
    # Must have durability fields
    if "durability" not in item_data or "max_durability" not in item_data:
        return False
    
    # Must not be broken
    if item_data.get("durability", 0) <= 0:
        return False
    
    # Must be a weapon or tool
    category = item_data.get("category", "")
    if category not in ("weapon", "tool"):
        return False
    
    return True