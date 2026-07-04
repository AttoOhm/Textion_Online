"""
Look Command (Phase 6B)

Short command: look [target]
Look at target or room.
- look → shows room description, exits, entities, actors
- look <entity> → shows entity details including container contents
- look <corpse> → shows corpse details including loot table

No long action. No tick cost. No action resolution.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.items import get_item_name


def handle_look(player_state, target_name, map_id, node_id, world_entities, actors_at_node, corpses, get_npc_data_func, get_actor_display_name_func, get_creature_display_name_func, is_actor_known_func):
    """Handle the 'look [target]' command.

    Args:
        player_state: Player state dict
        target_name: Name of target to look at (None for general look)
        map_id: Current map ID
        node_id: Current node ID
        world_entities: Dict of world entities
        actors_at_node: List of actor IDs at current node
        corpses: Dict of corpses
        get_npc_data_func: Function to get NPC data by ID
        get_actor_display_name_func: Function to get actor display name
        get_creature_display_name_func: Function to get creature display name
        is_actor_known_func: Function to check if actor is known

    Returns:
        Dict with command result
    """
    # General look (no target)
    if not target_name:
        return {
            "success": True,
            "type": "room",
            "message": "You look around.",
        }

    target_name_lower = target_name.lower().replace(' ', '_')

    # Check if target is an actor (NPC or creature)
    for actor_id in actors_at_node:
        if actor_id.lower() == target_name_lower:
            actor_data = get_npc_data_func(actor_id)
            if not actor_data:
                continue

            is_creature = actor_data.get('type') == 'creature'
            display_name = get_creature_display_name_func(actor_id, player_state) if is_creature else get_actor_display_name_func(actor_id, player_state)

            result = {
                "success": True,
                "type": "actor",
                "name": display_name,
                "description": actor_data.get('description', actor_data.get('dialogue_greeting', f"You see {display_name}.")),
                "details": {
                    "job": actor_data.get('conversation', {}).get('job', ''),
                    "species": actor_data.get('species', ''),
                    "type": actor_data.get('type', 'npc')
                }
            }

            # Include HP for creatures
            if is_creature:
                hp = actor_data.get('hp', 100)
                max_hp = actor_data.get('max_hp', 100)
                hp_percent = int((hp / max_hp) * 100) if max_hp > 0 else 0
                result['details']['hp'] = f"{hp}/{max_hp} ({hp_percent}%)"

            # Include attributes if available
            if 'attributes' in actor_data:
                result['attributes'] = actor_data['attributes']
            elif 'stats' in actor_data:
                result['attributes'] = actor_data['stats']

            # Include inventory/equipment if available
            items_list = []
            if 'inventory' in actor_data:
                inv = actor_data['inventory']
                if isinstance(inv, list):
                    for item in inv:
                        if isinstance(item, dict):
                            items_list.append(item.get('name', str(item)))
                        else:
                            items_list.append(str(item))
            elif 'equipment' in actor_data:
                for slot, item in actor_data['equipment'].items():
                    if item:
                        if isinstance(item, dict):
                            items_list.append(item.get('name', str(item)))
                        else:
                            items_list.append(str(item))
            result['items'] = items_list

            return result

    # Check if target is a corpse
    for corpse_id, corpse_data in corpses.items():
        corpse_display = corpse_data['display_name'].lower().replace(' ', '_')
        if corpse_display == target_name_lower or target_name_lower in corpse_display.split('_'):
            loot_table = corpse_data.get('loot_table', [])

            # Build loot list with chances
            items = []
            for loot_entry in loot_table:
                item_id = loot_entry.get('id', '')
                item_name = loot_entry.get('name', item_id)
                chance = loot_entry.get('chance', 1.0)
                chance_pct = int(chance * 100)
                items.append({
                    "name": item_name,
                    "chance": chance,
                    "chance_display": f"{chance_pct}%"
                })

            return {
                "success": True,
                "type": "corpse",
                "name": corpse_data['display_name'],
                "description": f"A {corpse_data['display_name'].lower()} corpse lies here.",
                "items": items,
                "can_loot": True
            }

    # Check if target is a world entity
    for ent_id, ent_data in world_entities.items():
        if ent_id.lower() == target_name_lower or ent_data.get('name', '').lower() == target_name_lower:
            result = {
                "success": True,
                "type": "entity",
                "name": ent_data.get('name', ent_id),
                "description": ent_data.get('description', f"You see {ent_id} here."),
                "details": ent_data.get('details', {})
            }

            # If entity has container contents, show them
            if 'contains' in ent_data:
                contains = ent_data['contains']
                items = []
                for item in contains:
                    item_id = item.get('id', '')
                    item_name = item.get('name', item_id)
                    chance = item.get('chance', 1.0)
                    chance_pct = int(chance * 100)
                    # Format: "Item Name (100%)" or just "Item Name" if 100%
                    if chance >= 1.0:
                        items.append(item_name)
                    else:
                        items.append(f"{item_name} ({chance_pct}%)")
                result['items'] = items
                result['can_take'] = True

            # If entity has items/contents, show them
            if 'items' in ent_data:
                result['items'] = ent_data['items']
            elif 'contents' in ent_data:
                result['items'] = ent_data['contents']

            return result

    # Target not found
    return {
        "success": False,
        "message": f"You don't see '{target_name}' here."
    }