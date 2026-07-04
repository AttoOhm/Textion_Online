"""
Take Command (Phase 6B)

Short command: take <item>
Take item from container or corpse.

No long action. No tick cost. No action resolution.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random

from engine.items import get_item_name


def handle_take(player_state, item_name, map_id, node_id, world_entities, corpses, get_npc_data_func, current_tick=0):
    """Handle the 'take <item>' command.

    Args:
        player_state: Player state dict
        item_name: Name of the item to take
        map_id: Current map ID
        node_id: Current node ID
        world_entities: Dict of world entities
        corpses: Dict of corpses
        get_npc_data_func: Function to get NPC data by ID
        current_tick: Current world tick

    Returns:
        Dict with command result
    """
    item_name_lower = item_name.lower().replace(' ', '_')
    actor_id = player_state.get("id", "player")

    # Ensure inventory exists
    if 'inventory' not in player_state:
        player_state['inventory'] = []

    # First check corpses at this location
    for corpse_id, corpse_data in corpses.items():
        if corpse_data['map_id'] == map_id and corpse_data['node_id'] == node_id:
            loot_table = corpse_data.get('loot_table', [])
            
            for loot_entry in loot_table:
                entry_id = loot_entry.get('id', '').lower().replace(' ', '_')
                entry_name = loot_entry.get('name', '')
                chance = loot_entry.get('chance', 1.0)
                
                # Check if this is the item player wants
                if entry_id == item_name_lower or entry_name.lower() == item_name_lower:
                    # Roll for chance
                    if random.random() < chance:
                        # Handle coins with min/max range
                        if entry_id == 'coins':
                            min_amount = loot_entry.get('min', 1)
                            max_amount = loot_entry.get('max', 10)
                            amount = random.randint(min_amount, max_amount)
                            player_state['coins'] = player_state.get('coins', 0) + amount
                            # Remove from corpse loot table
                            loot_table.remove(loot_entry)
                            if not loot_table:
                                del corpses[corpse_id]
                            return {
                                "success": True,
                                "message": f"You take {amount} coins from the {corpse_data['display_name']}.",
                                "item": f"{amount} coins"
                            }
                        else:
                            # Add to inventory
                            player_state['inventory'].append(entry_name)
                            # Remove from corpse loot table
                            loot_table.remove(loot_entry)
                        
                        # If corpse is now empty, remove it
                        if not loot_table:
                            del corpses[corpse_id]
                        
                        return {
                            "success": True,
                            "message": f"You take the {entry_name} from the {corpse_data['display_name']}.",
                            "item": entry_name
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"You search the {corpse_data['display_name']} but don't find a {entry_name}."
                        }

    # Then check world entities (containers) at this location
    for ent_id, ent_data in world_entities.items():
        # Check if entity is at this location
        ent_map = ent_data.get('map_id')
        ent_node = ent_data.get('node_id')
        
        if ent_map != map_id or ent_node != node_id:
            continue
        
        # Check if entity has container contents
        if 'contains' not in ent_data:
            continue
        
        contains = ent_data['contains']
        
        for item_entry in contains:
            entry_id = item_entry.get('id', '').lower().replace(' ', '_')
            entry_name = item_entry.get('name', '')
            chance = item_entry.get('chance', 1.0)
            
            # Check if this is the item player wants
            if entry_id == item_name_lower or entry_name.lower() == item_name_lower:
                # Roll for chance
                if random.random() < chance:
                    # Handle coins with min/max range
                    if entry_id == 'coins':
                        min_amount = item_entry.get('min', 1)
                        max_amount = item_entry.get('max', 10)
                        amount = random.randint(min_amount, max_amount)
                        player_state['coins'] = player_state.get('coins', 0) + amount
                        contains.remove(item_entry)
                        return {
                            "success": True,
                            "message": f"You take {amount} coins from the {ent_data.get('name', ent_id)}.",
                            "item": f"{amount} coins"
                        }
                    else:
                        # Add to inventory
                        player_state['inventory'].append(entry_name)
                        # Remove from container
                        contains.remove(item_entry)
                        
                        return {
                            "success": True,
                            "message": f"You take the {entry_name} from the {ent_data.get('name', ent_id)}.",
                            "item": entry_name
                        }
                else:
                    return {
                        "success": False,
                        "message": f"You search the {ent_data.get('name', ent_id)} but don't find a {entry_name}."
                    }

    # Item not found
    return {
        "success": False,
        "message": f"You don't see '{item_name}' here."
    }