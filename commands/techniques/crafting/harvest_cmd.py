"""
Harvest Command (Phase 7B)

Short command: harvest <resource>
Harvest berry bushes.

Requires:
- Sickle equipped (main_hand or off_hand)

Creates 1-tick Long Action.
No resolution. No skill checks. Deterministic.

At completion:
- Resource node quantity -1
- Inventory berry +1
- Tool durability -1
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.items import get_item_name


# Harvesting resources - Primary and Secondary food materials
HARVESTING_RESOURCES = [
    # Primary food materials
    "green_berry_bush",
    "red_berry_bush",
    "black_berry_bush",
    # Secondary food materials (grains)
    "wheat_field",
    "rice_field",
    "barley_field",
]

# Tool required
REQUIRED_TOOL = "sickle"

# Tool slot to check
TOOL_SLOTS = ["main_hand", "off_hand"]


def handle_harvest(player_state, resource_name, map_id, node_id,
                   resource_node_manager, inventory_engine, equipment_engine,
                   long_action_queue, current_tick=0):
    """Handle the 'harvest <resource>' command.

    Args:
        player_state: Player state dict
        resource_name: Name of resource to harvest (e.g., "blue berry bush")
        map_id: Current map ID
        node_id: Current node ID
        resource_node_manager: ResourceNodeManager instance
        inventory_engine: InventoryEngine instance
        equipment_engine: EquipmentEngine instance
        long_action_queue: ActionQueue instance
        current_tick: Current world tick

    Returns:
        Dict with command result
    """
    actor_id = player_state.get("id", "player")
    
    # Normalize resource name
    resource_name_lower = resource_name.lower().replace(" ", "_")
    
    # Check if resource exists in this location
    nodes = resource_node_manager.get_nodes_in_location(map_id, node_id)
    target_node = None
    for node in nodes:
        if node["node_type"] == resource_name_lower:
            target_node = node
            break
    
    if not target_node:
        return {
            "success": False,
            "message": f"You don't see '{resource_name}' here.",
        }
    
    # Check if node has quantity
    if not resource_node_manager.has_quantity(target_node["node_id"], 1):
        return {
            "success": False,
            "message": f"The {resource_name} has been fully harvested.",
        }
    
    # Check for required tool from player_state equipment
    tool_found = False
    tool_slot = None
    equipment = player_state.get("equipment", {})
    # Check both new slots (main_hand/off_hand) and legacy slots (weapon/armor/accessory)
    check_slots = TOOL_SLOTS + ["weapon", "armor", "accessory"]
    for slot in check_slots:
        equipped = equipment.get(slot)
        if not equipped:
            continue
        # Equipment can be stored as dict {"item_id": ..., "name": ...} or legacy string
        if isinstance(equipped, dict):
            item_id = equipped.get("item_id", "").lower()
            item_name = equipped.get("name", "").lower()
            if REQUIRED_TOOL in item_id or REQUIRED_TOOL in item_name:
                tool_found = True
                tool_slot = slot
                break
        elif isinstance(equipped, str):
            equipped_lower = equipped.lower()
            if REQUIRED_TOOL in equipped_lower:
                tool_found = True
                tool_slot = slot
                break

    if not tool_found:
        return {
            "success": False,
            "message": f"You need a {REQUIRED_TOOL} equipped to harvest.",
        }
    
    # Check tool durability (from equipment string - no durability tracking yet)
    # Tools don't have durability in current string-based equipment system
    # So we skip durability check for now
    
    # Determine output item
    output_item = get_harvesting_output(resource_name_lower)
    if not output_item:
        return {
            "success": False,
            "message": f"Unknown resource: {resource_name}",
        }
    
    # Check if actor already has active action
    existing_action = long_action_queue.get_actor_action(actor_id)
    if existing_action and existing_action["status"] in ("queued", "active"):
        return {
            "success": False,
            "message": "You are already performing an action.",
        }
    
    # Create 1-tick gathering action
    action = long_action_queue.queue_action(
        actor_id=actor_id,
        action_type="harvest",
        duration_ticks=0,
        current_tick=current_tick,
        parameters={
            "resource_node_id": target_node["node_id"],
            "resource_type": resource_name_lower,
            "output_item": output_item,
            "tool_slot": tool_slot,
        },
        resolution_config={},  # No resolution - deterministic
    )
    
    if not action:
        return {
            "success": False,
            "message": "Cannot start gathering action.",
        }
    
    return {
        "success": True,
        "message": f"You begin harvesting {resource_name}...",
        "action_id": action["action_id"],
        "end_tick": action["end_tick"],
    }


def complete_harvest(action, resource_node_manager, inventory_engine,
                     equipment_engine, current_tick=0):
    """Complete a harvesting action.

    Args:
        action: Completed long action dict
        resource_node_manager: ResourceNodeManager instance
        inventory_engine: InventoryEngine instance
        equipment_engine: EquipmentEngine instance
        current_tick: Current world tick

    Returns:
        Dict with completion result
    """
    actor_id = action["actor_id"]
    params = action["parameters"]
    
    resource_node_id = params["resource_node_id"]
    output_item = params["output_item"]
    tool_slot = params["tool_slot"]
    
    # Decrease resource quantity
    resource_node_manager.reduce_quantity(resource_node_id, 1)
    
    # Add to inventory (handle both InventoryEngine and raw list)
    if hasattr(inventory_engine, 'add_item'):
        inventory_engine.add_item(actor_id, output_item, 1, current_tick)
    elif isinstance(inventory_engine, list):
        inventory_engine.append(output_item)
    
    # Decrease tool durability (skip if no equipment_engine)
    if equipment_engine:
        tool_entry = equipment_engine.get_equipped_item(actor_id, tool_slot)
        if tool_entry:
            current_durability = tool_entry.get("durability", 100)
            new_durability = current_durability - 1
            tool_entry["durability"] = new_durability
            
            # Check if tool broke
            if new_durability <= 0:
                # Unequip broken tool
                equipment_engine.unequip_item(actor_id, tool_slot)
                return {
                    "success": True,
                    "message": f"You harvest the berries, but your {REQUIRED_TOOL} breaks!",
                    "tool_broken": True,
                }
    
    return {
        "success": True,
        "message": f"You harvest the berries and obtain {get_item_name(output_item)}.",
        "tool_broken": False,
    }


def get_harvesting_output(resource_type: str) -> str:
    """Get the output item for a harvesting resource.

    Args:
        resource_type: Resource node type (e.g., "blue_berry_bush")

    Returns:
        Output item ID, or empty string if unknown
    """
    harvesting_outputs = {
        # Primary food materials
        "green_berry_bush": "green_berry",
        "red_berry_bush": "red_berry",
        "black_berry_bush": "black_berry",
        # Secondary food materials
        "wheat_field": "wheat",
        "rice_field": "rice",
        "barley_field": "barley",
    }
    return harvesting_outputs.get(resource_type, "")
