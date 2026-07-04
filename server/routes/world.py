"""
World routes - world data loading and world update generation.
"""

from flask import request
from flask_socketio import emit
from server.state import (
    WORLD_MAPS, WORLD_ENTITIES, WORLD_ENTRANCES, ACTOR_POSITIONS,
    CREATURE_INSTANCES, player_states, player_sessions, corpses,
    creature_death_times, socketio, tick_number, resource_node_manager,
    conversation_memories
)
from engine.crafting import create_station
from server.state import get_player_state, get_game_time, get_game_hour, get_time_of_day
from server.state import get_actors_at_position, get_node
from server.state import get_npc_data, get_creature_display_name, get_actor_display_name, is_actor_known
from server.state import _items_db, pending_commands
import json
import os


@socketio.on('world_command')
def handle_game_command(data):
    """Handle game commands from client."""
    from server.state import get_player_state, get_actor_position, move_actor_to
    from server.state import get_npc_data, get_creature_display_name, get_actor_display_name
    from server.state import is_actor_known, ACTOR_POSITIONS, creature_death_times
    from server.state import player_sessions, player_states, get_actors_at_position
    
    sid = request.sid
    session = player_sessions.get(sid)
    
    if not session:
        emit('command_result', {'error': 'Not logged in'})
        return
    
    # Handle both old format (string) and new format (dict with account_id/player_id)
    if isinstance(session, dict):
        player_id = session.get('player_id')
    else:
        player_id = session
    
    if not player_id:
        emit('command_result', {'error': 'No character selected'})
        return
    
    state = get_player_state(player_id)
    cmd = data if isinstance(data, str) else data.get('command', '')
    parts = cmd.lower().strip().split()
    if not parts:
        return
    
    action = parts[0]
    args = parts[1:] if len(parts) > 1 else []
    
    result = {'message': ''}
    
    if action == 'look':
        # Send world update
        update = build_world_update_for_state(player_id, state)
        emit('world_update', update)
        return
    
    elif action == 'move':
        if not args:
            result['error'] = 'Move where?'
        else:
            # Skip 'to' if present (e.g., "move to village center" or "move village center")
            if args[0] == 'to' and len(args) > 1:
                dest = ' '.join(args[1:]).lower()
            else:
                dest = ' '.join(args).lower()
            pos = get_actor_position(player_id)
            
            if not pos:
                state_pos = state.get('position', {})
                if state_pos:
                    ACTOR_POSITIONS[player_id] = state_pos
                    pos = state_pos
            
            if not pos:
                result['error'] = 'You have no position'
            else:
                node = get_node(pos['map_id'], pos['node_id'])
                if not node:
                    result['error'] = 'Invalid position'
                else:
                    exits = node.get('exits', {})
                    # Check exact match, normalized match, and with "to " prefix (for exits like "to village center")
                    dest_normalized = dest.replace(' ', '_')
                    dest_with_to = f'to {dest}' if not dest.startswith('to ') else dest
                    if dest not in exits and dest_normalized not in exits and dest_with_to not in exits:
                        result['error'] = f'No exit "{dest}" here'
                    else:
                        # Check if already processing a movement queue
                        existing = pending_commands.get(player_id, [])
                        # Only queue if no movement command is already queued
                        has_move = any(c.strip().lower().startswith('move ') for c in existing)
                        if has_move:
                            result['error'] = 'You are already moving.'
                        else:
                            target_node = exits.get(dest) or exits.get(dest_normalized) or exits.get(dest_with_to)
                            # Queue movement for next tick processing
                            if player_id not in pending_commands:
                                pending_commands[player_id] = []
                            pending_commands[player_id].append(cmd)
                            result['message'] = f'[{cmd}] queued.'
    
    elif action == 'say':
        if not args:
            result['error'] = 'Say what?'
        else:
            message = ' '.join(args)
            pos = get_actor_position(player_id)
            if pos:
                # Broadcast to all players at same location
                for pid, pstate in player_states.items():
                    if pid != player_id:
                        ppos = pstate.get('position', {})
                        if ppos.get('map_id') == pos['map_id'] and ppos.get('node_id') == pos['node_id']:
                            emit('chat_message', {
                                'from': player_id,
                                'message': message,
                                'location': pos
                            }, room=player_sessions.get(pid))
    
    elif action == 'attack':
        if not args:
            result['error'] = 'Attack what?'
        else:
            # Queue attack for tick processing (uses full CombatEngine)
            if player_id not in pending_commands:
                pending_commands[player_id] = []
            pending_commands[player_id].append(cmd)
            result['message'] = f'[{cmd}] queued.'
    
    elif action == 'disconnect':
        result['message'] = 'Disconnecting...'
        # Force disconnect this socket
        from server.state import socketio
        socketio.disconnect(request.sid)
    
    elif action == 'help':
        result['message'] = 'Commands: look, move [direction], say [message], attack [target], talk to [npc], shop, equip [item], unequip [item/slot], inventory, journal, quests, inspect [target], disconnect, help'
    
    elif action == 'journal':
        # Show player's quest journal
        state.setdefault('quests', [])
        state.setdefault('completed_quests', [])
        state.setdefault('quest_notes', {})
        
        # Deduplicate active quests by id
        seen_ids = set()
        unique_active = []
        for q in state.get('quests', []):
            qid = q.get('id', '')
            if qid and qid not in seen_ids:
                seen_ids.add(qid)
                unique_active.append(q)
        if len(unique_active) != len(state.get('quests', [])):
            state['quests'] = unique_active
        
        active_quests = [q for q in state.get('quests', []) if q.get('status') == 'active']
        completed_quests = state.get('completed_quests', [])
        quest_notes = state.get('quest_notes', {})
        
        if not active_quests and not completed_quests:
            result['message'] = 'Your journal is empty. Talk to NPCs to find quests.'
        else:
            lines = ['=== Quest Journal ===']
            
            if active_quests:
                lines.append('\nActive Quests:')
                for quest in active_quests:
                    q_name = quest.get('name') or quest.get('id', 'Unknown Quest')
                    q_id = quest.get('id', '')
                    note = quest_notes.get(q_id, '')
                    lines.append(f"  - {q_name}")
                    if note:
                        lines.append(f"    Note: {note}")
            
            if completed_quests:
                lines.append('\nCompleted Quests:')
                for quest in completed_quests:
                    q_name = quest.get('name') or quest.get('id', 'Unknown Quest')
                    lines.append(f"  - {q_name}")
            
            result['message'] = '\n'.join(lines)
    
    elif action == 'quests':
        # Alias for journal
        result['message'] = 'Use "journal" to view your quests.'
    
    elif action == 'shop':
        # Shop command - works when talking to an NPC with a shop
        pos = get_actor_position(player_id)
        if not pos:
            result['error'] = 'You have no position'
        else:
            actors_here = get_actors_at_position(pos['map_id'], pos['node_id'])
            shopper = None
            for actor_id in actors_here:
                actor_data = get_npc_data(actor_id)
                if actor_data:
                    world = actor_data.get('world') or {}
                    shop = world.get('shop') or {}
                    items = shop.get('items', [])
                    if items:
                        shopper = actor_data
                        break
            if shopper:
                sname = shopper.get('name', 'They')
                shop = (shopper.get('world') or {}).get('shop') or {}
                items = shop.get('items', [])
                lines = [f"{sname} gestures to his wares."]
                for item in items:
                    if not item.get('secret', False):
                        lines.append(f"  {item['name']} - {item.get('stats', '')} - {item['price']} coins")
                lines.append(f"{sname} says: 'I've got what you see here.'")
                result['message'] = '\n'.join(lines)
            else:
                result['error'] = 'There is no one here with a shop to browse.'
    
    elif action in ('enter', 'exit'):
        # Handle entrance/exit to travel between maps
        pos = get_actor_position(player_id)
        if not pos:
            result['error'] = 'You have no position'
        else:
            # Find entrance at current location
            entrance = None
            for ent_id, ent_data in WORLD_ENTRANCES.items():
                if ent_data.get('map_id') == pos['map_id'] and ent_data.get('node_id') == pos['node_id']:
                    entrance = ent_data
                    break
            
            if entrance:
                dest_map = entrance.get('destination_map')
                dest_node = entrance.get('destination_node')
                state['position'] = {'map_id': dest_map, 'node_id': dest_node}
                ACTOR_POSITIONS[player_id] = {'map_id': dest_map, 'node_id': dest_node}
                from server.state import discover_node
                discover_node(state, dest_node)
                result['message'] = f'You {action} via {entrance.get("name", "the entrance")}.'
                # Follow up with a look
                from server.state import socketio
                update = build_world_update_for_state(player_id, state)
                emit('world_update', update)
                return
            else:
                # Check if node_name (like "south") matches an entrance's node_id
                for ent_id, ent_data in WORLD_ENTRANCES.items():
                    if ent_data.get('node_id') and action in ent_data.get('node_id', '').lower():
                        entrance = ent_data
                        break
                # Also check if args[0] matches an entrance node_id
                if not entrance and args:
                    arg = ' '.join(args).lower().replace(' ', '_')
                    for ent_id, ent_data in WORLD_ENTRANCES.items():
                        ent_node = ent_data.get('node_id', '').lower()
                        ent_name = ent_data.get('name', '').lower().replace(' ', '_')
                        if arg in ent_node or arg in ent_name:
                            entrance = ent_data
                            break
                
                if entrance:
                    dest_map = entrance.get('destination_map')
                    dest_node = entrance.get('destination_node')
                    state['position'] = {'map_id': dest_map, 'node_id': dest_node}
                    ACTOR_POSITIONS[player_id] = {'map_id': dest_map, 'node_id': dest_node}
                    from server.state import discover_node
                    discover_node(state, dest_node)
                    result['message'] = f'You {action} via {entrance.get("name", "the entrance")}.'
                    update = build_world_update_for_state(player_id, state)
                    emit('world_update', update)
                    return
                else:
                    result['error'] = 'No entrance here.'
    
    elif action == 'equip':
        if not args:
            result['error'] = 'Equip what?'
        else:
            item_name_display = ' '.join(args).lower()
            item_name_lower = item_name_display.replace(' ', '_')
            inventory = state.get('inventory', [])
            item_index = None
            canonical_id = None
            
            for i, inv_item in enumerate(inventory):
                if isinstance(inv_item, str):
                    if inv_item.lower() == item_name_display or inv_item.lower() == item_name_lower:
                        item_index = i
                        canonical_id = inv_item.lower().replace(' ', '_')
                        break
                elif isinstance(inv_item, dict):
                    iid = inv_item.get('item_id', '').lower()
                    iname = inv_item.get('name', '').lower()
                    if iid == item_name_lower or iid == item_name_display or iname == item_name_display:
                        item_index = i
                        canonical_id = iid or item_name_lower
                        break
            
            if item_index is None:
                result['error'] = f"You don't have {item_name_display} in your inventory."
            else:
                # Look up item data by canonical ID
                db_item = _items_db.get(canonical_id)
                if not db_item:
                    for key, itm in _items_db.items():
                        if isinstance(itm, dict) and itm.get('id', '').lower() == canonical_id:
                            db_item = itm
                            break
                
                if db_item:
                    item_category = db_item.get('category', '').lower()
                    item_subtype = db_item.get('subtype', '').lower()
                    display_name = db_item.get('name', item_name_display.title())
                    canonical_id = db_item.get('id', canonical_id)
                else:
                    item_category = ''
                    item_subtype = ''
                    display_name = item_name_display.title()
                
                equipment = state.setdefault('equipment', {})
                slot = None
                
                if item_category == 'weapon' or item_subtype in ['sword', 'dagger', 'axe', 'hammer', 'bow', 'staff', 'wand']:
                    slot = 'main_hand'
                elif item_category == 'armor':
                    slot = 'armor'
                elif item_category == 'container' and item_subtype == 'quiver':
                    slot = 'off_hand'
                
                if not slot:
                    if any(kw in item_name_display for kw in ['sword', 'dagger', 'axe', 'hammer', 'bow', 'staff', 'wand']):
                        slot = 'main_hand'
                    elif any(kw in item_name_display for kw in ['hatchet', 'pickaxe', 'sickle', 'tool']):
                        slot = 'main_hand'
                    elif any(kw in item_name_display for kw in ['shield', 'buckler']):
                        slot = 'off_hand'
                    elif any(kw in item_name_display for kw in ['armor', 'robe', 'tunic', 'cuirass']):
                        slot = 'armor'
                
                if not slot:
                    result['error'] = f"You cannot equip {item_name_display}."
                else:
                    inventory.pop(item_index)
                    current_equipped = equipment.get(slot)
                    if current_equipped:
                        inventory.append(current_equipped)
                    
                    equipment[slot] = {"item_id": canonical_id, "name": display_name}
                    result['message'] = f"You equip {display_name}."
    
    elif action == 'unequip':
        if not args:
            result['error'] = 'Unequip what?'
        else:
            target = ' '.join(args).lower()
            equipment = state.setdefault('equipment', {})
            inventory = state.setdefault('inventory', [])
            slot_key = target.replace(' ', '_')
            if slot_key in equipment:
                item_entry = equipment.get(slot_key)
                if item_entry:
                    iname = item_entry.get('name', item_entry.get('item_id', str(item_entry)))
                    inventory.append(iname)
                    equipment[slot_key] = None
                    result['message'] = f"You unequip {iname} from your {target}."
                else:
                    result['error'] = f"Nothing is equipped in your {target}."
            else:
                found_slot = None
                for slot, item in equipment.items():
                    if item:
                        iname = item.get('name', item.get('item_id', str(item))).lower()
                        if iname == target:
                            found_slot = slot
                            break
                if found_slot:
                    item_entry = equipment[found_slot]
                    iname = item_entry.get('name', item_entry.get('item_id', str(item_entry)))
                    inventory.append(iname)
                    equipment[found_slot] = None
                    result['message'] = f"You unequip {iname}."
                else:
                    result['error'] = f"{target.title()} is not equipped."
    
    elif action == 'talk':
        if not args or args[0] != 'to':
            result['error'] = 'Usage: talk to [npc]'
        else:
            npc_name = ' '.join(args[1:]) if len(args) > 1 else ''
            if not npc_name:
                result['error'] = 'Talk to whom?'
            else:
                # Handle talk to logic here
                from server.state import get_actors_at_position, reveal_actor_identity
                pos = get_actor_position(player_id)
                if not pos:
                    result['error'] = 'You have no position'
                else:
                    actors_here = get_actors_at_position(pos['map_id'], pos['node_id'])
                    npc_id = npc_name.lower()
                    npc_id_underscore = npc_id.replace(' ', '_')
                    matched = None
                    for actor_id in actors_here:
                        actor_lower = actor_id.lower()
                        # Check both spaced and underscore forms
                        if actor_lower == npc_id or actor_lower == npc_id_underscore:
                            matched = actor_id
                            break
                        actor_data = get_npc_data(actor_id)
                        if actor_data:
                            display = get_actor_display_name(actor_id, state).lower().replace('a ', '').replace('an ', '').replace(' is here', '')
                            # Also try matching against the raw unknown_name
                            appearance = actor_data.get('appearance', {})
                            unknown_name = appearance.get('unknown_name', '').lower().replace('a ', '').replace('an ', '').replace(' ', '_')
                            if (npc_id in display or display in npc_id or
                                npc_id_underscore in display or display in npc_id_underscore or
                                npc_id in unknown_name or unknown_name in npc_id or
                                npc_id_underscore in unknown_name or unknown_name in npc_id_underscore):
                                matched = actor_id
                                break
                    
                    if not matched:
                        result['error'] = f'{npc_name.title()} is not here.'
                    else:
                        npc_data = get_npc_data(matched)
                        actual_name = npc_data.get('name', matched) if npc_data else matched
                        if npc_data:
                            appearance = npc_data.get('appearance', {})
                            conversation = npc_data.get('conversation', {})
                            
                            # Check if player has met this NPC before
                            mem = conversation_memories.get(player_id, {}).get(matched, None)
                            has_met_before = mem is not None and len(mem.get('history', [])) > 0
                            
                            if has_met_before:
                                # Player knows them - use known_name or full_name
                                actual_name = appearance.get('known_name') or appearance.get('full_name') or npc_data.get('name', matched)
                                greeting = conversation.get('greeting', f"{actual_name} nods at you.")
                            else:
                                # First meeting - use NPC's actual name in greeting, unknown_name in activity
                                actual_name = appearance.get('unknown_name', f"a {conversation.get('job', 'person')}")
                                npc_real_name = npc_data.get('name', matched)
                                # Use first_greeting if available, otherwise default with NPC's real name
                                greeting = conversation.get('first_greeting', f"{npc_real_name} looks at you.")
                        else:
                            actual_name = matched
                            greeting = f"The {actual_name} looks at you."
                        
                        # Initialize conversation memory for subsequent npc_chat messages
                        if player_id not in conversation_memories:
                            conversation_memories[player_id] = {}
                        if matched not in conversation_memories[player_id]:
                            conversation_memories[player_id][matched] = {
                                'history': [], 'state': 'general', 'childish_warnings': 0
                            }
                        mem = conversation_memories[player_id][matched]
                        mem['history'].append({'speaker': 'npc', 'text': greeting})
                        mem['current_npc'] = matched
                        # Reveal identity so display name switches to known_name
                        if not has_met_before:
                            reveal_actor_identity(state, matched)
                        emit('npc_conversation', {'activity': f"You approach {actual_name}.", 'greeting': greeting})
                        return
    
    elif action == 'reload':
        # Reload world data from disk (fixes stale map cache)
        global WORLD_MAPS
        WORLD_MAPS.clear()
        load_world_data()
        result['message'] = 'World data reloaded from disk.'
        # Re-send world update
        update = build_world_update_for_state(player_id, state)
        emit('world_update', update)
        return
    
    elif action == 'inspect':
        if not args:
            result['error'] = 'Inspect what?'
        else:
            inspect_target = ' '.join(args).lower().replace(' ', '_')
            inspect_result = _handle_inspect(player_id, inspect_target, state)
            result['message'] = inspect_result.get('message', '')
            if inspect_result.get('error'):
                result['error'] = inspect_result['error']
    
    elif action in ('chop', 'mine', 'harvest', 'smelt', 'craft', 'grind', 'saw', 'repair', 'learn', 'close', 'drink'):
        # Queue commands for tick processing
        if player_id not in pending_commands:
            pending_commands[player_id] = []
        pending_commands[player_id].append(cmd)
        result['message'] = f'[{cmd}] queued.'
    
    else:
        result['error'] = f'Unknown command: {action}'
    
    emit('command_result', result)


def load_world_data():
    """Load all world data from files."""
    global WORLD_MAPS, WORLD_ENTITIES, WORLD_ENTRANCES, ACTOR_POSITIONS
    print("[WORLD] Module loaded - game_command handler registered")
    
    # Load maps
    maps_dir = os.path.join('data', 'world', 'maps')
    if os.path.exists(maps_dir):
        for filename in os.listdir(maps_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(maps_dir, filename)
                with open(filepath, 'r') as f:
                    map_data = json.load(f)
                    if not isinstance(map_data, dict) or 'id' not in map_data or 'nodes' not in map_data:
                        continue
                    WORLD_MAPS[map_data['id']] = map_data
    
    # Load entities
    entities_dir = os.path.join('data', 'world', 'entities')
    if os.path.exists(entities_dir):
        for filename in os.listdir(entities_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(entities_dir, filename)
                with open(filepath, 'r') as f:
                    entity_data_map = json.load(f)
                    for entity_id, entity_data in entity_data_map.items():
                        WORLD_ENTITIES[entity_id] = entity_data
                        
                        # Register stations with resource_node_manager
                        if entity_data.get('station_type'):
                            station = create_station(
                                station_id=entity_id,
                                station_type=entity_data['station_type'],
                                name=entity_data.get('name', entity_id),
                                map_id=entity_data.get('map_id', ''),
                                node_id=entity_data.get('node_id', '')
                            )
                            if station:
                                resource_node_manager.add_station(station)
    
    # Load entrances
    entrances_path = os.path.join('data', 'world', 'entrances.json')
    if os.path.exists(entrances_path):
        with open(entrances_path, 'r') as f:
            data = json.load(f)
            WORLD_ENTRANCES = data.get('entrances', {})
    
    # Note: Actor/NPC loading is handled by server/state.py load_all_npcs()
    # which properly handles schedules and max_distance constraints
    
    print(f"[WORLD] Loaded {len(WORLD_MAPS)} maps, {len(WORLD_ENTITIES)} entities, {len(WORLD_ENTRANCES)} entrances")


def _process_movement_queues():
    """Process all player movement queues and execute one movement per tick."""
    global ACTOR_POSITIONS
    
    for player_id, state in player_states.items():
        queue = state.get('movement_queue', [])
        if not queue:
            continue
        
        # Process only ONE movement per tick
        movement = queue.pop(0)
        
        from_node = movement['from_node']
        to_node = movement['node']
        map_id = movement['map_id']
        
        # Update position
        ACTOR_POSITIONS[player_id] = {'map_id': map_id, 'node_id': node}
        state['position'] = {'map_id': map_id, 'node_id': node}
        
        print(f"[MOVEMENT] {player_id} moved from {from_node} to {node}")
        
        # Clear remaining queue if any (only one movement per tick)
        if queue:
            state['movement_queue'] = []
            print(f"[MOVEMENT] Cleared remaining movement queue for {player_id}")


def _handle_loot(player_id, loot_target, state):
    """Handle looting a corpse.
    
    Args:
        player_id: Player attempting to loot
        loot_target: Corpse ID to loot
        state: Player state
        
    Returns:
        Dict with message or error
    """
    import server.state as st
    
    # Find the corpse
    corpse_data = None
    corpse_id = None
    for cid, cdata in corpses.items():
        if cid.lower().replace(' ', '_') == loot_target or cid == loot_target:
            corpse_data = cdata
            corpse_id = cid
            break
    
    if not corpse_data:
        return {'error': 'Corpse not found.'}
    
    # Check if player is at the corpse location
    pos = state.get('position', {})
    if pos.get('map_id') != corpse_data['map_id'] or pos.get('node_id') != corpse_data['node_id']:
        return {'error': 'You are not at the corpse location.'}
    
    loot_table = corpse_data.get('loot_table', [])
    if not loot_table:
        return {'error': 'The corpse has no loot.'}
    
    # Check if this is a player corpse
    is_player_corpse = corpse_data.get('is_player_corpse', False)
    owner_id = corpse_data.get('owner_id')
    
    # Separate loot into player-only and public
    player_only_items = []
    public_items = []
    
    for item in loot_table:
        if item.get('owner_only', False):
            player_only_items.append(item)
        else:
            public_items.append(item)
    
    # Determine what this player can loot
    can_loot_private = (not is_player_corpse) or (owner_id == player_id)
    
    available_loot = []
    if can_loot_private:
        available_loot.extend(player_only_items)
    available_loot.extend(public_items)
    
    if not available_loot:
        if is_player_corpse and owner_id != player_id:
            return {'error': 'This is not your corpse. Only the public item can be looted.'}
        else:
            return {'error': 'The corpse has already been looted.'}
    
    # Loot all available items
    inventory = state.setdefault('inventory', [])
    looted_items = []
    
    for item in available_loot:
        item_id = item.get('item_id', '')
        item_name = item.get('name', 'Unknown')
        quantity = item.get('quantity', 1)
        
        if item_id == 'coins':
            # Add coins to player's coin count
            state['coins'] = state.get('coins', 0) + quantity
            looted_items.append(f"{quantity} coins")
        else:
            # Add item to inventory
            inventory.append({
                'item_id': item_id,
                'name': item_name,
                'quantity': quantity
            })
            looted_items.append(item_name)
    
    # Remove looted items from corpse
    remaining_loot = []
    for item in loot_table:
        if item in available_loot:
            continue  # Skip looted items
        remaining_loot.append(item)
    
    if remaining_loot:
        corpses[corpse_id]['loot_table'] = remaining_loot
    else:
        # Remove empty corpse
        del corpses[corpse_id]
        print(f"[LOOT] Corpse {corpse_id} fully looted and removed.")
    
    # Format message
    if len(looted_items) == 1:
        msg = f"You loot {looted_items[0]} from the corpse."
    else:
        items_str = ', '.join(looted_items[:-1]) + f" and {looted_items[-1]}"
        msg = f"You loot {items_str} from the corpse."
    
    return {'message': msg}


def _handle_inspect(player_id, inspect_target, state):
    """Handle inspecting a corpse to see its contents.
    
    Args:
        player_id: Player inspecting
        inspect_target: Corpse ID to inspect
        state: Player state
        
    Returns:
        Dict with message or error
    """
    # Find the corpse
    corpse_data = None
    for cid, cdata in corpses.items():
        if cid.lower().replace(' ', '_') == inspect_target or cid == inspect_target:
            corpse_data = cdata
            break
    
    if not corpse_data:
        return {'error': 'Corpse not found.'}
    
    # Check if player is at the corpse location
    pos = state.get('position', {})
    if pos.get('map_id') != corpse_data['map_id'] or pos.get('node_id') != corpse_data['node_id']:
        return {'error': 'You are not at the corpse location.'}
    
    loot_table = corpse_data.get('loot_table', [])
    if not loot_table:
        return {'message': 'The corpse has no loot.'}
    
    # Check if this is a player corpse
    is_player_corpse = corpse_data.get('is_player_corpse', False)
    owner_id = corpse_data.get('owner_id')
    is_owner = (owner_id == player_id)
    
    # Build inspection message
    lines = [f"You inspect {corpse_data['display_name']}:"]
    
    player_only_items = []
    public_items = []
    
    for item in loot_table:
        if item.get('owner_only', False):
            player_only_items.append(item)
        else:
            public_items.append(item)
    
    if public_items:
        lines.append("\nPublic items (anyone can take):")
        for item in public_items:
            item_name = item.get('name', 'Unknown')
            quantity = item.get('quantity', 1)
            if quantity > 1:
                lines.append(f"  - {item_name} (x{quantity})")
            else:
                lines.append(f"  - {item_name}")
    
    if player_only_items:
        if is_owner:
            lines.append("\nYour items (only you can take):")
            for item in player_only_items:
                item_name = item.get('name', 'Unknown')
                quantity = item.get('quantity', 1)
                if quantity > 1:
                    lines.append(f"  - {item_name} (x{quantity})")
                else:
                    lines.append(f"  - {item_name}")
        else:
            lines.append("\nPrivate items (only the owner can take these)")
    
    if not public_items and not player_only_items:
        lines.append("  (empty)")
    
    return {'message': '\n'.join(lines)}


def _handle_take(player_id, take_target, state):
    """Handle taking items from a corpse.
    
    Args:
        player_id: Player taking items
        take_target: Corpse ID to take from
        state: Player state
        
    Returns:
        Dict with message or error
    """
    import server.state as st
    
    # Find the corpse
    corpse_data = None
    corpse_id = None
    for cid, cdata in corpses.items():
        if cid.lower().replace(' ', '_') == take_target or cid == take_target:
            corpse_data = cdata
            corpse_id = cid
            break
    
    if not corpse_data:
        return {'error': 'Corpse not found.'}
    
    # Check if player is at the corpse location
    pos = state.get('position', {})
    if pos.get('map_id') != corpse_data['map_id'] or pos.get('node_id') != corpse_data['node_id']:
        return {'error': 'You are not at the corpse location.'}
    
    loot_table = corpse_data.get('loot_table', [])
    if not loot_table:
        return {'error': 'The corpse has no loot.'}
    
    # Check if this is a player corpse
    is_player_corpse = corpse_data.get('is_player_corpse', False)
    owner_id = corpse_data.get('owner_id')
    is_owner = (owner_id == player_id)
    
    # Separate loot into player-only and public
    player_only_items = []
    public_items = []
    
    for item in loot_table:
        if item.get('owner_only', False):
            player_only_items.append(item)
        else:
            public_items.append(item)
    
    # Determine what this player can take
    can_take_private = (not is_player_corpse) or is_owner
    
    available_loot = []
    if can_take_private:
        available_loot.extend(player_only_items)
    available_loot.extend(public_items)
    
    if not available_loot:
        if is_player_corpse and not is_owner:
            return {'error': 'This is not your corpse. Only the public item can be taken.'}
        else:
            return {'error': 'The corpse has already been looted.'}
    
    # Take all available items
    inventory = state.setdefault('inventory', [])
    taken_items = []
    
    for item in available_loot:
        item_id = item.get('item_id', '')
        item_name = item.get('name', 'Unknown')
        quantity = item.get('quantity', 1)
        
        if item_id == 'coins':
            # Add coins to player's coin count
            state['coins'] = state.get('coins', 0) + quantity
            taken_items.append(f"{quantity} coins")
        else:
            # Add item to inventory
            inventory.append({
                'item_id': item_id,
                'name': item_name,
                'quantity': quantity
            })
            taken_items.append(item_name)
    
    # Remove taken items from corpse
    remaining_loot = []
    for item in loot_table:
        if item in available_loot:
            continue  # Skip taken items
        remaining_loot.append(item)
    
    if remaining_loot:
        corpses[corpse_id]['loot_table'] = remaining_loot
    else:
        # Remove empty corpse
        del corpses[corpse_id]
        print(f"[LOOT] Corpse {corpse_id} fully looted and removed.")
    
    # Format message
    if len(taken_items) == 1:
        msg = f"You take {taken_items[0]} from the corpse."
    else:
        items_str = ', '.join(taken_items[:-1]) + f" and {taken_items[-1]}"
        msg = f"You take {items_str} from the corpse."
    
    return {'message': msg}


def _process_creature_respawns():
    """Check respawn queue and respawn creatures whose timer has expired."""
    global ACTOR_POSITIONS, creature_death_times, CREATURE_INSTANCES, tick_number
    
    respawned = []
    for instance_id, death_tick in list(creature_death_times.items()):
        instance_data = CREATURE_INSTANCES.get(instance_id)
        if not instance_data:
            continue
        
        respawn_minutes = instance_data.get('respawn_minutes', 10)
        respawn_tick = death_tick + (respawn_minutes * 60)
        
        if tick_number >= respawn_tick:
            spawn_point = instance_data.get('spawn_point', {})
            map_id = spawn_point.get('map_id')
            node_id = spawn_point.get('node_id')
            
            if map_id and node_id:
                ACTOR_POSITIONS[instance_id] = {'map_id': map_id, 'node_id': node_id}
                del creature_death_times[instance_id]
                respawned.append(instance_id)
                print(f"[RESPAWN] Creature '{instance_id}' has respawned at {map_id}/{node_id}")
    
    if respawned:
        print(f"[RESPAWN] Respawned {len(respawned)} creatures this tick: {respawned}")


# World update sequence counter (to filter stale buffered messages on reconnect)
_world_update_sequence = 0

def build_world_update_for_state(player_id, state):
    """Build world_update payload for a player."""
    global _world_update_sequence
    _world_update_sequence += 1
    pos = state.get('position', {'map_id': 'village', 'node_id': 'village_center'})
    map_id = pos['map_id']
    node_id = pos['node_id']
    
    node = get_node(map_id, node_id)
    description = node.get('description', f'You are at {node.get("name", node_id)}.') if node else ''
    exits = list(node.get('exits', {}).keys()) if node else []
    events = []
    
    # Show world objects/entities at this node
    if node:
        for ent in node.get('entities', []):
            entity_data = WORLD_ENTITIES.get(ent)
            display_name = ent.replace('_', ' ').title()
            if entity_data:
                events.append(entity_data.get('description', f"You see {display_name} here."))
            else:
                events.append(f"You see {display_name} here.")
    
    # Show available entrances
    for ent_id, ent_data in WORLD_ENTRANCES.items():
        if ent_data.get('map_id') == map_id and ent_data.get('node_id') == node_id:
            events.append(f"📍 {ent_data.get('name', 'Entrance')}: {ent_data.get('description', '')}")
    
    # Show actors at this location (exclude self)
    actors_here = get_actors_at_position(map_id, node_id)
    actors_present = []  # List of {actor_id, display_name} for clickable names
    for actor_id in actors_here:
        # Skip self - player doesn't need to see themselves listed
        if actor_id == player_id:
            continue
        actor_data = get_npc_data(actor_id)
        if actor_data and actor_data.get('type') == 'creature':
            display_name = get_creature_display_name(actor_id, state)
            events.append(f"You see {display_name} here.")
            actors_present.append({"actor_id": actor_id, "display_name": display_name})
        elif actor_data:
            display_name = get_actor_display_name(actor_id, state)
            # Try world.job first, then fall back to conversation.job, then 'villager'
            job = (actor_data.get('world', {}) or {}).get('job', '') or (actor_data.get('conversation', {}) or {}).get('job', 'villager')
            # Always show NPC name, add job title if known
            if is_actor_known(state, actor_id):
                events.append(f"{display_name} the {job} is here.")
            else:
                events.append(f"{display_name} is here.")
            actors_present.append({"actor_id": actor_id, "display_name": display_name})
        else:
            # Skip if this is another player (handled by the dedicated "other players" section below)
            if actor_id in player_states:
                continue
            display_name = get_actor_display_name(actor_id, state)
            events.append(f"{display_name} is here.")
            actors_present.append({"actor_id": actor_id, "display_name": display_name})
    
    # Show other players at this location (multiplayer)
    other_players = []
    for other_player_id, other_state in player_states.items():
        if other_player_id != player_id:
            other_pos = other_state.get('position', {})
            if other_pos.get('map_id') == map_id and other_pos.get('node_id') == node_id:
                other_players.append(other_player_id)
    
    if other_players:
        for other_pid in other_players:
            other_state = player_states.get(other_pid, {})
            other_name = other_state.get('name', other_pid)
            # Skip players in world update (they're handled separately)
            if other_name in player_states:
                continue
            events.append(f"👤 {other_name} is here.")
    
    # Show corpses
    for corpse_id, corpse_data in corpses.items():
        if corpse_data['map_id'] == map_id and corpse_data['node_id'] == node_id:
            events.append(f"💀 {corpse_data['display_name']} corpse lies here. (loot it)")
    
    # Debug: Show corpse count
    if corpses:
        print(f"[WORLD] Showing {len(corpses)} corpses to {player_id} at {map_id}/{node_id}")
    
    # Calculate day number (1 day = 24 hours = 1440 game minutes)
    day_number = 1 + (tick_number // 1440)
    
    return {
        'time': get_game_time(),
        'day': day_number,
        'map_id': map_id,
        'node_id': node_id,
        'location': node.get('name', node_id) if node else node_id,
        'narration': description,
        'events': events,
        'exits': exits,
        'actors_present': actors_present,  # For clickable actor names
        'seq': _world_update_sequence  # Sequence number to filter stale messages
    }
