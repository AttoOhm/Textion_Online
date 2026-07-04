"""
Craft Command (Phase 7D)

Short command: craft <item>
Craft finished items from refined materials.

Requires:
- Recipe knowledge (learned)
- Required technique known
- Required materials in inventory
- Required station present

Creates 1d6 tick Long Action.
No resolution. No skill checks. Deterministic.

At completion:
- Materials removed from inventory
- Finished item added to inventory
- Material familiarity increased
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.items import get_item_name
import random


# Required station for crafting
REQUIRED_STATION = None  # Set per recipe

# Required technique for crafting
REQUIRED_TECHNIQUE = None  # Set per recipe

# Duration: 1d6 ticks
MIN_DURATION = 1
MAX_DURATION = 6


def handle_craft(player_state, item_name, map_id, node_id,
                 resource_node_manager, inventory_engine, equipment_engine,
                 disciplines_engine, recipe_manager, long_action_queue,
                 familiarity_engine, actor_id, current_tick=0):
    """Handle the 'craft <item>' command.

    Args:
        player_state: Player state dict
        item_name: Name of item to craft (e.g., "iron sword")
        map_id: Current map ID
        node_id: Current node ID
        resource_node_manager: ResourceNodeManager instance
        inventory_engine: InventoryEngine instance
        equipment_engine: EquipmentEngine instance
        disciplines_engine: DisciplinesEngine instance
        recipe_manager: RecipeManager instance
        long_action_queue: ActionQueue instance
        familiarity_engine: FamiliarityEngine instance
        current_tick: Current world tick

    Returns:
        Dict with command result
    """
    
    # Normalize item name
    item_name_lower = item_name.lower().replace(" ", "_")
    
    # Check if recipe exists
    recipe = recipe_manager.get_recipe_definition(item_name_lower)
    if not recipe:
        return {
            "success": False,
            "message": f"You don't know how to craft '{item_name}'.",
        }
    
    # Check if actor has learned this recipe (from player_state, not recipe_manager)
    known_recipes = player_state.get('known_recipes', [])
    if item_name_lower not in known_recipes:
        return {
            "success": False,
            "message": f"You haven't learned the recipe for '{item_name}'.",
        }
    
    # Get recipe details (canonical schema)
    technique = recipe.get("technique_required")
    station = recipe.get("station_required")
    materials = recipe.get("inputs", [])
    outputs = recipe.get("outputs", [])
    output_item = outputs[0]["item"] if outputs else None
    
    # Check if actor has required technique (from player_state, not technique_manager)
    actor_techniques = player_state.get('techniques', {})
    if technique not in actor_techniques:
        return {
            "success": False,
            "message": f"You need to know the {technique} technique.",
        }
    
    # Check if required station is present in current node
    if not _is_station_present(map_id, node_id, station, resource_node_manager):
        return {
            "success": False,
            "message": f"You must be near a {station.replace('_', ' ')} to craft {item_name}.",
        }
    
    # Check if actor has required materials
    for material in materials:
        mat_item = material["item"]
        mat_qty = material["quantity"]
        if not inventory_engine.has_item(actor_id, mat_item, mat_qty):
            return {
                "success": False,
                "message": f"You need {mat_qty} {mat_item} to craft {item_name}.",
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
    
    # Create crafting Long Action
    action = long_action_queue.queue_action(
        actor_id=actor_id,
        action_type="craft",
        duration_ticks=duration,
        current_tick=current_tick,
        parameters={
            "recipe_id": item_name_lower,
            "output_item": output_item,
            "technique": technique,
            "station_type": station,
            "materials": materials,
        },
        resolution_config={},  # No resolution - deterministic
    )
    
    if not action:
        return {
            "success": False,
            "message": "Cannot start crafting action.",
        }
    
    return {
        "success": True,
        "message": f"You begin crafting {item_name}...",
        "action_id": action["action_id"],
        "end_tick": action["end_tick"],
        "duration": duration,
    }


def complete_craft(action, inventory_engine, familiarity_engine, current_tick=0, player_state=None):
    """Complete a crafting action.

    Args:
        action: Completed long action dict
        inventory_engine: InventoryEngine instance
        familiarity_engine: FamiliarityEngine instance
        current_tick: Current world tick
        player_state: Player state dict (for character name)

    Returns:
        Dict with completion result
    """
    actor_id = action["actor_id"]
    params = action["parameters"]
    
    # Get character name for crafted_by
    character_name = actor_id
    if player_state:
        character_name = player_state.get('name', actor_id)
    
    output_item = params["output_item"]
    materials = params["materials"]
    
    # Calculate quality based on material familiarity
    quality_tier, quality_score = _calculate_quality(materials, familiarity_engine, actor_id)
    
    # Calculate durability modifier based on quality
    durability_modifier = _get_durability_modifier(quality_tier)
    
    # Remove materials
    for material in materials:
        mat_item = material["item"]
        mat_qty = material["quantity"]
        inventory_engine.remove_item(actor_id, mat_item, mat_qty, current_tick)
    
    # Add finished item with quality
    from engine.items import get_item_definition
    base_item = get_item_definition(output_item)
    
    item_data = {
        "item_id": output_item,
        "quality": quality_tier,
        "crafted_by": character_name,
    }
    
    # Add base item stats (damage, weight, etc.)
    if base_item:
        for stat in ["damage", "weight", "armor", "magic_resist", "durability", "max_durability"]:
            if stat in base_item:
                item_data[stat] = base_item[stat]
    
    inventory_engine.add_item_with_quality(actor_id, output_item, 1, current_tick, 
                                          quality=quality_tier, durability_modifier=durability_modifier)
    
    # Increase familiarity for each material used
    familiarity_gains = []
    for material in materials:
        mat_item = material["item"]
        # Only increase familiarity for refined materials (not raw resources)
        if _is_refined_material(mat_item):
            familiarity_engine.increase_familiarity(actor_id, mat_item, current_tick)
            familiarity_gains.append(mat_item)
    
    # Build result message
    material_names = ", ".join([m["item"] for m in materials])
    message = f"You craft {get_item_name(output_item)} using {material_names}."
    
    # Add quality to message
    if quality_tier != "junior":
        message += f" Quality: {quality_tier.title()}."
    
    if familiarity_gains:
        fam_names = ", ".join(familiarity_gains)
        message += f" Familiarity increased: {fam_names}."
    
    return {
        "success": True,
        "message": message,
        "quality": quality_tier,
        "quality_score": quality_score,
        "familiarity_increased": familiarity_gains,
    }


def _is_station_present(map_id: str, node_id: str, station_type: str, resource_node_manager) -> bool:
    """Check if a required station is present in the current node.
    
    Args:
        map_id: Current map ID
        node_id: Current node ID
        station_type: Type of station required (e.g., "anvil")
        resource_node_manager: ResourceNodeManager instance
        
    Returns:
        True if station is present, False otherwise
    """
    # Use ResourceNodeManager's station tracking
    return resource_node_manager.has_station_type(map_id, node_id, station_type)


def _is_refined_material(item_id: str) -> bool:
    """Check if an item is a refined material (not raw resource).
    
    Refined materials increase familiarity when used in crafting.
    Raw resources (ores, logs, berries) do not.
    
    Args:
        item_id: Item ID to check
        
    Returns:
        True if refined material, False if raw resource
    """
    # Raw resources (gathered directly)
    raw_resources = [
        # Ores
        "copper_ore", "iron_ore", "mithril_ore",
        "tin_ore", "coal_ore", "dragonite_ore",
        # Logs
        "oak_log", "ash_log", "yew_log",
        # Berries
        "green_berry", "red_berry", "black_berry",
        # Grains
        "wheat", "rice", "barley",
        # Resins
        "resin", "sap", "spirit_bark",
    ]
    
    if item_id in raw_resources:
        return False
    
    # Everything else is considered refined
    # (ingots, planks, mash, advanced materials)
    return True


def _calculate_quality(materials: list, familiarity_engine, actor_id: str) -> tuple:
    """Calculate quality tier based on material familiarity.
    
    Quality is based ONLY on material familiarity.
    No crafting XP, recipe XP, technique XP, or character level.
    
    Args:
        materials: List of material dicts with "item" and "quantity"
        familiarity_engine: MaterialFamiliarityTracker instance
        actor_id: Actor crafting the item
        
    Returns:
        Tuple of (quality_tier, quality_score)
        quality_tier: "junior", "journeyman", "senior", or "master"
        quality_score: Average familiarity score used for calculation
    """
    # Calculate average familiarity across all materials
    total_familiarity = 0
    material_count = 0
    
    for material in materials:
        mat_item = material["item"]
        familiarity = familiarity_engine.get_familiarity(actor_id, mat_item)
        total_familiarity += familiarity
        material_count += 1
    
    # Calculate average
    if material_count == 0:
        average_familiarity = 0
    else:
        average_familiarity = total_familiarity / material_count
    
    # Determine quality tier based on average familiarity
    if average_familiarity >= 15:
        # Master roll: 25% chance for Master, otherwise Senior
        if random.random() < 0.25:
            quality_tier = "master"
        else:
            quality_tier = "senior"
    elif average_familiarity >= 10:
        quality_tier = "senior"
    elif average_familiarity >= 5:
        quality_tier = "journeyman"
    else:
        quality_tier = "junior"
    
    return quality_tier, average_familiarity


def _get_durability_modifier(quality_tier: str) -> float:
    """Get durability modifier based on quality tier.
    
    Args:
        quality_tier: Quality tier ("junior", "journeyman", "senior", "master")
        
    Returns:
        Durability modifier (multiplier)
    """
    modifiers = {
        "junior": 0.90,      # -10% max durability
        "journeyman": 1.00,  # Normal durability
        "senior": 1.10,      # +10% max durability
        "master": 1.25,      # +25% max durability
    }
    
    return modifiers.get(quality_tier, 1.00)
