"""
Learn Command (Phase 7D)

Short command: learn recipe <item>
Learn a crafting recipe.

Requires:
- Recipe exists in recipe manager
- Actor does not already know it

No cost.
No station required.
No technique required.

At completion:
- Recipe added to actor's known recipes
- Can now craft the item
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def handle_learn(player_state, recipe_name, actor_id, recipe_manager, inventory_engine=None):
    """Handle the 'learn recipe <item>' command.

    Args:
        player_state: Player state dict
        recipe_name: Name of recipe to learn (e.g., "iron sword")
        actor_id: Actor learning the recipe
        recipe_manager: RecipeManager instance
        inventory_engine: InventoryEngine instance (optional, for consuming recipe items)

    Returns:
        Dict with command result
    """
    # Normalize recipe name (strip "recipe" prefix/suffix if user typed variations)
    recipe_name_lower = recipe_name.lower().replace(" ", "_")
    # Remove "recipe:" or "recipe_" prefix (handle "recipe: oak_bow" -> "oak_bow")
    if recipe_name_lower.startswith("recipe:"):
        recipe_name_lower = recipe_name_lower[7:]  # Remove "recipe:" prefix
        recipe_name_lower = recipe_name_lower.lstrip("_")  # Remove leading underscore if present
        recipe_name_lower = recipe_name_lower.lstrip(":")  # Remove any remaining colons
    elif recipe_name_lower.startswith("recipe_"):
        recipe_name_lower = recipe_name_lower[7:]  # Remove "recipe_" prefix
    # Remove "_recipe" suffix
    if recipe_name_lower.endswith("_recipe"):
        recipe_name_lower = recipe_name_lower[:-7]  # Remove "_recipe" suffix
    
    # Check if recipe exists in definitions
    if not recipe_manager.has_recipe_definition(recipe_name_lower):
        return {
            "success": False,
            "message": f"Unknown recipe: '{recipe_name}'.",
        }
    
    # Check if actor already knows this recipe (from player_state, not recipe_manager)
    known_recipes = player_state.get('known_recipes', [])
    if recipe_name_lower in known_recipes:
        return {
            "success": False,
            "message": f"You already know how to craft '{recipe_name}'.",
        }
    
    # Check if player has a recipe item in inventory
    recipe_item_id = f"recipe_{recipe_name_lower}"
    if inventory_engine and inventory_engine.has_item(actor_id, recipe_item_id):
        # Consume the recipe item
        inventory_engine.remove_item(actor_id, recipe_item_id, 1, 0)
        message = f"You study the recipe and learn how to craft {recipe_name}."
    else:
        # No recipe item - just learn it directly (for backward compatibility)
        message = f"You learn the recipe for {recipe_name}."
    
    # Add to player's known recipes
    known_recipes.append(recipe_name_lower)
    player_state['known_recipes'] = known_recipes
    
    return {
        "success": True,
        "message": message,
        "recipe_id": recipe_name_lower,
    }
