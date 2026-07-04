"""
Inspect Command - View and take items from containers/corpses.

Usage:
  inspect <target>     - Open inspection window for target
  take <item> [qty]    - Take item from inspected container
  close                - Close inspection window
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def handle_inspect(player_state, target_name, actor_id, world_entities, corpses, inspect_state, inventory_engine):
    """Handle the 'inspect <target>' command.
    
    Args:
        player_state: Player state dict
        target_name: Name of target to inspect (e.g., "corpse wolf_alpha" or "weapon rack")
        actor_id: Actor inspecting
        world_entities: WORLD_ENTITIES dict from server state
        corpses: corpses dict from server state
        inspect_state: inspect_state dict from server state
        inventory_engine: InventoryEngine instance
        
    Returns:
        Dict with command result
    """
    import re
    # Normalize target name
    target_name_lower = target_name.lower().replace(' ', '_')
    
    # Check if already inspecting something
    if actor_id in inspect_state:
        return {
            "success": False,
            "message": f"You are already inspecting {inspect_state[actor_id].get('display_name', 'something')}. Type 'close' first."
        }
    
    # Observation check: if another player is already inspecting this target, you can't inspect it
    # unless you have higher observation
    player_observation = player_state.get('attributes', {}).get('observation', 50)
    for other_actor_id, other_inspection in inspect_state.items():
        if other_actor_id == actor_id:
            continue
        # Check if inspecting the same target
        other_target = other_inspection.get('target_id', '')
        if other_target == target_name_lower or other_target in target_name_lower or target_name_lower in other_target:
            # Get other player's observation
            other_player_state = None
            # We need to access player_states, but it's not passed in
            # For now, use a default value - this could be improved
            other_observation = 50  # Default
            if player_observation <= other_observation:
                return {
                    "success": False,
                    "message": f"Someone else is already inspecting that. You need better observation to compete.",
                    "inspect_open": False
                }
    
    # Try to find target in corpses
    target_data = None
    target_display = None
    found_corpse_id = None
    
    if target_name_lower.startswith('corpse_') or 'corpse' in target_name_lower:
        # Search for corpse by ID or display name
        search_term = target_name_lower.replace('corpse_', '').replace('corpse', '').strip('_').strip()
        # Remove numeric suffix for matching (e.g., "grey_wolf_1" -> "grey_wolf")
        search_term_clean = re.sub(r'_\d+$', '', search_term)
        
        for corpse_id, corpse_data in corpses.items():
            corpse_display = corpse_data.get('display_name', '').lower().replace(' ', '_')
            corpse_id_lower = corpse_id.lower()
            corpse_id_clean = re.sub(r'_\d+$', '', corpse_id_lower)
            # Also clean numeric suffix from display name (e.g., "grey_wolf_1" from "Grey Wolf 1")
            corpse_display_clean = re.sub(r'_\d+$', '', corpse_display)
            
            # Match by cleaned ID or display name
            if (corpse_id_clean == search_term_clean or 
                search_term_clean in corpse_id_clean or
                search_term_clean in corpse_display_clean or
                corpse_display_clean == search_term_clean or
                search_term_clean in corpse_display):
                target_data = corpse_data
                target_display = corpse_data.get('display_name', corpse_id)
                found_corpse_id = corpse_id
                break
        
        if not target_data:
            return {
                "success": False,
                "message": f"No corpse '{target_name}' here."
            }
    else:
        # Try to find in world entities
        # First check if target_name matches an entity ID
        if target_name_lower in world_entities:
            entity_data = world_entities[target_name_lower]
            if 'contains' in entity_data:
                target_data = {
                    'entity_id': target_name_lower,
                    'contains': entity_data['contains'],
                    'map_id': entity_data.get('map_id'),
                    'node_id': entity_data.get('node_id')
                }
                target_display = entity_data.get('name', target_name_lower.replace('_', ' ').title())
            else:
                return {
                    "success": False,
                    "message": f"You cannot inspect the {target_name}."
                }
        else:
            # Try partial match on entity names
            for entity_id, entity_data in world_entities.items():
                entity_name = entity_data.get('name', '').lower().replace(' ', '_')
                if target_name_lower in entity_name or entity_name in target_name_lower:
                    if 'contains' in entity_data:
                        target_data = {
                            'entity_id': entity_id,
                            'contains': entity_data['contains'],
                            'map_id': entity_data.get('map_id'),
                            'node_id': entity_data.get('node_id')
                        }
                        target_display = entity_data.get('name', entity_id.replace('_', ' ').title())
                        break
            
            if not target_data:
                return {
                    "success": False,
                    "message": f"You don't see '{target_name}' here."
                }
    
    # Check if target is at player's location
    pos = player_state.get('position', {})
    p_map = pos.get('map_id', 'village')
    p_node = pos.get('node_id', 'village_center')
    
    target_map = target_data.get('map_id')
    target_node = target_data.get('node_id')
    
    if target_map and target_node:
        if target_map != p_map or target_node != p_node:
            return {
                "success": False,
                "message": f"{target_display} is not here."
            }
    
    # Lock target to player
    inspect_state[actor_id] = {
        'target_id': target_name_lower,
        'target_data': target_data,
        'display_name': target_display,
        'corpse_id': found_corpse_id
    }
    
    # Build item list - corpses use 'loot_table', world entities use 'contains'
    if 'loot_table' in target_data:
        items = target_data.get('loot_table', [])
    else:
        items = target_data.get('contains', [])
    
    return {
        "success": True,
        "message": f"Inspecting: {target_display}",
        "inspect_open": True,
        "target": target_display,
        "items": items
    }


def handle_take(player_state, item_name, qty, actor_id, inspect_state, inventory_engine, corpses=None):
    """Handle the 'take <item>' command during inspection.
    
    Args:
        player_state: Player state dict
        item_name: Name of item to take
        qty: Quantity to take (default 1)
        actor_id: Actor taking item
        inspect_state: inspect_state dict from server state
        inventory_engine: InventoryEngine instance
        corpses: corpses dict from server state (optional, for syncing loot changes)
        
    Returns:
        Dict with command result
    """
    # Check if player has active inspection
    if actor_id not in inspect_state:
        return {
            "success": False,
            "message": "You are not inspecting anything. Type 'inspect <target>' first."
        }
    
    inspection = inspect_state[actor_id]
    target_data = inspection['target_data']
    target_display = inspection['display_name']
    
    # Get items from target - corpses use 'loot_table', world entities use 'contains'
    if 'loot_table' in target_data:
        items = target_data.get('loot_table', [])
    else:
        items = target_data.get('contains', [])
    if not items:
        return {
            "success": False,
            "message": f"{target_display} is empty.",
            "inspect_open": True
        }
    
    # Determine the source key for syncing back to corpses dict
    is_corpse = 'loot_table' in target_data
    
    # Find item to take
    item_name_lower = item_name.lower().replace(' ', '_')
    matched_item = None
    for item in items:
        item_id = item.get('id', '').lower().replace(' ', '_')
        item_name_field = item.get('name', '').lower().replace(' ', '_')
        # Match by id or name, with flexible spacing
        if item_id == item_name_lower or item_name_field == item_name_lower:
            matched_item = item
            break
        # Also try matching with underscores vs spaces
        item_id_underscore = item_id.replace('_', ' ')
        if item_id_underscore == item_name or item_id == item_name_lower:
            matched_item = item
            break
    
    if not matched_item:
        # Debug: show what items are actually available
        available = [f"{i.get('name', i.get('id', '?'))}" for i in items]
        return {
            "success": False,
            "message": f"{target_display} doesn't contain '{item_name}'. Available: {', '.join(available)}",
            "inspect_open": True
        }
    
    # Get item details
    item_id = matched_item.get('id', item_name_lower)
    item_display_name = matched_item.get('name', item_id.replace('_', ' ').title())
    
    # Check if player has room (for non-stackable items, just check if exists)
    from engine.items import is_stackable, get_max_stack
    if is_stackable(item_id):
        # Stackable - just add to inventory
        inventory_engine.add_item(actor_id, item_id, qty, 0)
    else:
        # Non-stackable - check if already has one
        if inventory_engine.has_item(actor_id, item_id):
            return {
                "success": False,
                "message": f"You already have {item_display_name}.",
                "inspect_open": True
            }
        inventory_engine.add_item(actor_id, item_id, 1, 0)
    
    # Remove from container
    items.remove(matched_item)
    
    # Sync changes back to global corpses dict if this is a corpse
    if is_corpse and corpses is not None:
        corpse_id = inspect_state[actor_id].get('corpse_id')
        if corpse_id and corpse_id in corpses:
            corpses[corpse_id]['loot_table'] = items
    
    # Update player inventory in state
    player_state['inventory'] = inventory_engine._inventories.get(actor_id, player_state.get('inventory', []))
    
    # Check if container is now empty - use the synced items list
    if not items:
        # Get corpse ID for cleanup
        corpse_id = inspection.get('corpse_id')
        # Clear inspection and mark for removal
        inspect_result = {
            "success": True,
            "message": f"You take {item_display_name}. {target_display} is now empty.",
            "inspect_open": False,  # Close window
            "target": target_display,
            "items": [],
            "corpse_empty": True,  # Flag to remove corpse
            "corpse_id": corpse_id  # Pass corpse ID for cleanup
        }
        # Clear the inspection
        if actor_id in inspect_state:
            del inspect_state[actor_id]
        return inspect_result
    
    return {
        "success": True,
        "message": f"You take the {item_display_name}.",
        "inspect_open": True,
        "target": target_display,
        "items": items
    }


def handle_close(player_state, actor_id, inspect_state):
    """Handle the 'close' command to close inspection.
    
    Args:
        player_state: Player state dict
        actor_id: Actor closing inspection
        inspect_state: inspect_state dict from server state
        
    Returns:
        Dict with command result
    """
    if actor_id not in inspect_state:
        return {
            "success": False,
            "message": "You are not inspecting anything."
        }
    
    target_display = inspect_state[actor_id].get('display_name', 'target')
    del inspect_state[actor_id]
    
    return {
        "success": True,
        "message": f"You close your inspection of {target_display}.",
        "inspect_open": False
    }