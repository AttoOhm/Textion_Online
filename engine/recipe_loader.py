"""
Recipe Loader (Phase 7D)

Loads recipe definitions from JSON data files into the RecipeManager.

Supports:
- Finished crafting recipes (blacksmithing, woodcrafting)
- Future recipe types (alchemy, runestones, etc.)

Reuses:
- engine/recipe_manager.py
"""

import json
import os
import sys
from typing import Dict, List, Any

# Import recipe manager
try:
    from engine.recipe_manager import RecipeManager, create_recipe_knowledge
except ImportError:
    from recipe_manager import RecipeManager, create_recipe_knowledge


def load_recipes_from_json(recipe_manager: RecipeManager, json_file_path: str) -> int:
    """Load recipes from a JSON file into the recipe manager.
    
    Args:
        recipe_manager: RecipeManager instance to load into
        json_file_path: Path to JSON recipe file
        
    Returns:
        Number of recipes successfully loaded
    """
    if not os.path.exists(json_file_path):
        print(f"Warning: Recipe file not found: {json_file_path}")
        return 0
    
    with open(json_file_path, 'r') as f:
        recipe_data = json.load(f)
    
    loaded_count = 0
    
    # Iterate through recipe categories (blacksmithing, woodcrafting, etc.)
    for category_name, category_data in recipe_data.items():
        technique = category_data.get("technique", "")
        station = category_data.get("station", "")
        recipes = category_data.get("recipes", {})
        
        # Load each recipe in the category
        for recipe_id, recipe_info in recipes.items():
            # Create recipe definition
            recipe_def = create_recipe_knowledge(
                recipe_id=recipe_id,
                name=recipe_info.get("name", recipe_id),
                station_required=station,
                technique_required=technique,
                inputs=recipe_info.get("inputs", []),
                outputs=recipe_info.get("outputs", [{"item": recipe_id, "quantity": 1}]),
                duration_ticks=recipe_info.get("duration_ticks", 5),
            )
            
            # Register recipe
            if recipe_manager.register_recipe(recipe_def):
                loaded_count += 1
    
    return loaded_count


def load_all_recipes(recipe_manager: RecipeManager, base_path: str = "data/recipes") -> Dict[str, int]:
    """Load all recipe files from a directory.
    
    Args:
        recipe_manager: RecipeManager instance to load into
        base_path: Base directory containing recipe JSON files
        
    Returns:
        Dict mapping filename to number of recipes loaded
    """
    results = {}
    
    if not os.path.exists(base_path):
        print(f"Warning: Recipe directory not found: {base_path}")
        return results
    
    # Load all JSON files in the recipes directory
    for filename in os.listdir(base_path):
        if filename.endswith('.json'):
            file_path = os.path.join(base_path, filename)
            loaded = load_recipes_from_json(recipe_manager, file_path)
            results[filename] = loaded
    
    return results


def get_recipe_categories(recipe_manager: RecipeManager) -> Dict[str, List[str]]:
    """Get recipes organized by technique/category.
    
    Args:
        recipe_manager: RecipeManager instance
        
    Returns:
        Dict mapping technique name to list of recipe IDs
    """
    categories: Dict[str, List[str]] = {}
    
    for recipe_id, recipe_def in recipe_manager._recipe_definitions.items():
        technique = recipe_def.get("technique_required", "unknown")
        if technique not in categories:
            categories[technique] = []
        categories[technique].append(recipe_id)
    
    return categories


def print_recipe_summary(recipe_manager: RecipeManager):
    """Print a summary of all loaded recipes.
    
    Args:
        recipe_manager: RecipeManager instance
    """
    categories = get_recipe_categories(recipe_manager)
    
    print("=" * 60)
    print("LOADED RECIPES")
    print("=" * 60)
    
    total_recipes = 0
    for technique, recipe_ids in sorted(categories.items()):
        print(f"\n{technique.upper()}:")
        for recipe_id in sorted(recipe_ids):
            recipe_def = recipe_manager.get_recipe_definition(recipe_id)
            if recipe_def:
                name = recipe_def.get("name", recipe_id)
                station = recipe_def.get("station_required", "unknown")
                print(f"  - {name} ({recipe_id}) @ {station}")
                total_recipes += 1
    
    print(f"\nTotal recipes loaded: {total_recipes}")
    print("=" * 60)


# ============ DEMO / VALIDATION ============


def run_demo():
    """Demonstrate recipe loading."""
    print("=" * 60)
    print("RECIPE LOADER DEMO")
    print("=" * 60)
    
    # Create recipe manager
    rm = RecipeManager()
    
    # Load recipes from JSON
    base_path = os.path.join(os.path.dirname(__file__), "..", "data", "recipes")
    results = load_all_recipes(rm, base_path)
    
    print("\nLoading results:")
    for filename, count in results.items():
        print(f"  {filename}: {count} recipes")
    
    # Print summary
    print_recipe_summary(rm)
    
    # Test recipe lookup
    print("\n--- Recipe Lookup Test ---")
    iron_sword = rm.get_recipe_definition("iron_sword")
    if iron_sword:
        print(f"Iron Sword recipe found:")
        print(f"  Technique: {iron_sword['technique_required']}")
        print(f"  Station: {iron_sword['station_required']}")
        print(f"  Inputs: {iron_sword['inputs']}")
        print(f"  Outputs: {iron_sword['outputs']}")
    
    # Test recipe knowledge
    print("\n--- Recipe Knowledge Test ---")
    learned = rm.learn_recipe("player", "iron_sword")
    print(f"Learned iron_sword: {learned}")
    
    knows = rm.knows_recipe("player", "iron_sword")
    print(f"Player knows iron_sword: {knows}")
    
    known_recipes = rm.get_known_recipes("player")
    print(f"Player knows {len(known_recipes)} recipe(s)")


if __name__ == "__main__":
    run_demo()