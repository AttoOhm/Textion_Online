"""
Item Engine (Phase 6A)

Supports item definitions from existing items.json.
Do not create a second item database.

This module provides:
- Item definition loading
- Item validation
- Item queries
"""

import json
import os
from typing import Optional, Dict, List, Any

# ============ CONSTANTS ============

ITEMS_FILE = os.path.join("data", "objects", "items.json")

# Item types
ITEM_TYPE_WEAPON = "weapon"
ITEM_TYPE_ARMOR = "armor"
ITEM_TYPE_POTION = "potion"
ITEM_TYPE_FOOD = "food"
ITEM_TYPE_KEY = "key"
ITEM_TYPE_CURRENCY = "currency"
ITEM_TYPE_MISC = "misc"

# Stacking rules
STACKABLE_TYPES = ["potion", "food", "currency", "misc"]
NON_STACKABLE_TYPES = ["weapon", "armor", "key"]

# ============ ITEM DEFINITIONS ============

_item_definitions: Dict[str, Dict[str, Any]] = {}


def load_items():
    """Load item definitions from items.json and data/objects/ subdirectories."""
    global _item_definitions
    _item_definitions = {}

    # Load from items.json if it exists
    if os.path.exists(ITEMS_FILE):
        with open(ITEMS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for category in ["weapons", "armor", "consumables", "misc"]:
            items = data.get(category, [])
            for item in items:
                item_id = item.get("id")
                if item_id:
                    _item_definitions[item_id] = item

    # Load from data/objects/ subdirectories (materials, weapons, misc, etc.)
    objects_dir = os.path.join("data", "objects")
    if os.path.exists(objects_dir):
        for subdir in os.listdir(objects_dir):
            subdir_path = os.path.join(objects_dir, subdir)
            if os.path.isdir(subdir_path):
                for filename in os.listdir(subdir_path):
                    if filename.endswith('.json'):
                        filepath = os.path.join(subdir_path, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            try:
                                data = json.load(f)
                                # Handle both {category: [items]} and direct list formats
                                if isinstance(data, dict):
                                    for category, items in data.items():
                                        if isinstance(items, list):
                                            for item in items:
                                                item_id = item.get("id")
                                                if item_id:
                                                    _item_definitions[item_id] = item
                                elif isinstance(data, list):
                                    for item in data:
                                        item_id = item.get("id")
                                        if item_id:
                                            _item_definitions[item_id] = item
                            except Exception as e:
                                print(f"[ITEMS] Warning: Failed to load {filepath}: {e}")

    print(f"[ITEMS] Loaded {len(_item_definitions)} item definitions")


def get_item_definition(item_id: str) -> Optional[Dict[str, Any]]:
    """Get an item definition by ID.

    Args:
        item_id: Item identifier

    Returns:
        Item definition dict or None
    """
    if not _item_definitions:
        load_items()
    return _item_definitions.get(item_id)


def item_exists(item_id: str) -> bool:
    """Check if an item definition exists.

    Args:
        item_id: Item identifier

    Returns:
        True if item exists
    """
    return get_item_definition(item_id) is not None


def get_item_type(item_id: str) -> str:
    """Get the type of an item.

    Args:
        item_id: Item identifier

    Returns:
        Item type string
    """
    item = get_item_definition(item_id)
    if item:
        return item.get("type", "misc")
    return "misc"


def get_item_name(item_id: str) -> str:
    """Get the name of an item.

    Args:
        item_id: Item identifier

    Returns:
        Item name string
    """
    item = get_item_definition(item_id)
    if item:
        return item.get("name", item_id)
    return item_id


def get_item_subtype(item_id: str) -> str:
    """Get the subtype of an item.

    Args:
        item_id: Item identifier

    Returns:
        Item subtype string
    """
    item = get_item_definition(item_id)
    if item:
        return item.get("subtype", "")
    return ""


def is_stackable(item_id: str) -> bool:
    """Check if an item is stackable.
    
    Checks item definition first for explicit 'stackable' field,
    then falls back to type-based rules.

    Args:
        item_id: Item identifier

    Returns:
        True if item is stackable
    """
    item = get_item_definition(item_id)
    if item and 'stackable' in item:
        return item['stackable']
    item_type = get_item_type(item_id)
    return item_type in STACKABLE_TYPES


def get_max_stack(item_id: str) -> int:
    """Get the maximum stack size for an item.
    
    Returns 128 for stackable items without explicit max_stack,
    1 for non-stackable items.

    Args:
        item_id: Item identifier

    Returns:
        Maximum stack size
    """
    if not is_stackable(item_id):
        return 1
    
    item = get_item_definition(item_id)
    if item and 'max_stack' in item:
        return item['max_stack']
    
    return 128  # Default max stack


def validate_item(item_id: str) -> List[str]:
    """Validate an item definition. Returns list of errors (empty = valid)."""
    errors = []
    item = get_item_definition(item_id)
    if not item:
        errors.append(f"Item '{item_id}' not found")
        return errors
    if "id" not in item:
        errors.append("Item missing 'id'")
    if "name" not in item:
        errors.append("Item missing 'name'")
    if "type" not in item:
        errors.append("Item missing 'type'")
    return errors


def get_all_items() -> Dict[str, Dict[str, Any]]:
    """Get all item definitions.

    Returns:
        Dict of item_id -> item definition
    """
    if not _item_definitions:
        load_items()
    return dict(_item_definitions)