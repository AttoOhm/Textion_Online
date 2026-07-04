"""
Entity routes - entity lookups and interaction.
"""

from flask import request
from flask_socketio import emit
from server.state import (
    socketio, player_sessions, player_states
)
from server.state import get_player_state, WORLD_ENTITIES, WORLD_ENTRANCES
from server.state import get_node, get_actors_at_position, get_npc_data
from server.state import get_creature_display_name, get_actor_display_name, is_actor_known
from server.state import get_quest_data, _quest_cache
from server.state import conversation_memories, reveal_actor_identity
from server.npc_conversation import handle_npc_conversation
from server.routes.world import build_world_update_for_state


# All command handling is now in world.py via the world_command event
# This file only handles get_npc_conversation and npc_chat events


@socketio.on('get_npc_conversation')
def handle_get_npc_conversation(npc_name):
    """Handle NPC conversation start."""
    print(f"[GET_NPC] Received request for: {npc_name}")
    npc_id = npc_name.lower()
    npc_id_underscore = npc_id.replace(' ', '_')
    sid = request.sid
    session = player_sessions.get(sid)
    print(f"[GET_NPC] Session: {session}")
    
    # Handle both old format (string) and new format (dict)
    if isinstance(session, dict):
        player_id = session.get('player_id')
    else:
        player_id = session
    
    if not player_id:
        return
    
    state = get_player_state(player_id)
    pos = state.get('position', {'map_id': 'village', 'node_id': 'village_center'})
    p_map, p_node = pos['map_id'], pos['node_id']
    actors_here = get_actors_at_position(p_map, p_node)
    
    # Try to find the NPC by ID or display name
    matched_npc_id = None
    for actor_id in actors_here:
        actor_lower = actor_id.lower()
        # Check both exact match (with spaces) and underscore-normalized match
        if actor_lower == npc_id or actor_lower == npc_id_underscore:
            matched_npc_id = actor_id
            break
        # Check if the search term matches the NPC's role/job (partial matching)
        actor_data = get_npc_data(actor_id)
        if actor_data:
            # Direct check against actor ID (e.g. "grim")
            if npc_id in actor_id or npc_id_underscore in actor_id:
                matched_npc_id = actor_id
                break
            display_name = get_actor_display_name(actor_id, state).lower()
            # Remove "a " and " is here" parts for matching
            display_clean = display_name.replace('a ', '').replace(' is here', '')
            if npc_id in display_clean or display_clean in npc_id or npc_id_underscore in display_clean or display_clean in npc_id_underscore:
                matched_npc_id = actor_id
                break
            # Check against job/role directly from NPC data
            world_data = actor_data.get('world') or {}
            job = (world_data.get('job', '') or '').lower()
            if job and (npc_id == job or npc_id == job.replace(' ', '_') or npc_id_underscore == job or npc_id_underscore == job.replace(' ', '_')):
                matched_npc_id = actor_id
                break
            conv = actor_data.get('conversation') or {}
            job = (conv.get('job', '') or '').lower()
            if job and (npc_id == job or npc_id == job.replace(' ', '_') or npc_id_underscore == job or npc_id_underscore == job.replace(' ', '_')):
                matched_npc_id = actor_id
                break
    
    if not matched_npc_id:
        emit('command_result', {'error': f'{npc_name.title()} is not here.'})
        return
    
    npc_data = get_npc_data(matched_npc_id)
    if npc_data:
        appearance = npc_data.get('appearance', {})
        conversation = npc_data.get('conversation', {})
        
        # Check if player has met this NPC before
        mem = conversation_memories.get(player_id, {}).get(matched_npc_id, None)
        has_met_before = mem is not None and len(mem.get('history', [])) > 0
        
        # Determine which name to use based on whether player knows them
        if has_met_before:
            # Player knows them - use known_name or full_name
            actual_name = appearance.get('known_name') or appearance.get('full_name') or npc_data.get('name', matched_npc_id)
            greeting = conversation.get('greeting', f"{actual_name} nods at you.")
        else:
            # First meeting - use unknown_name
            actual_name = appearance.get('unknown_name', f"a {conversation.get('job', 'person')}")
            first_greeting = conversation.get('first_greeting', f"The {actual_name} looks at you.")
            greeting = first_greeting
        
        # Store greeting in conversation history
        if player_id not in conversation_memories:
            conversation_memories[player_id] = {}
        if matched_npc_id not in conversation_memories[player_id]:
            conversation_memories[player_id][matched_npc_id] = {
                'history': [], 'state': 'general', 'childish_warnings': 0
            }
        mem = conversation_memories[player_id][matched_npc_id]
        mem['history'].append({'speaker': 'npc', 'text': greeting})
        mem['current_npc'] = matched_npc_id  # Store for subsequent messages
        
        emit('npc_conversation', {'activity': f"You approach {actual_name}.", 'greeting': greeting})


@socketio.on('npc_chat')
def handle_npc_chat(data):
    """Handle NPC chat message."""
    npc_name = data.get('npcName', '')
    message = data.get('message', '')
    print(f"[NPC_CHAT] Received: npcName='{npc_name}', message='{message}'")
    npc_id = npc_name.lower()
    npc_id_underscore = npc_id.replace(' ', '_')
    print(f"[NPC_CHAT] Normalized npc_id: '{npc_id}'")
    # Remove article prefixes that might cause matching issues
    if npc_id.startswith('a_') or npc_id.startswith('an_'):
        npc_id = npc_id.split('_', 1)[1]
        print(f"[NPC_CHAT] After article removal: '{npc_id}'")
    sid = request.sid
    session = player_sessions.get(sid)
    
    # Handle both old format (string) and new format (dict)
    if isinstance(session, dict):
        player_id = session.get('player_id')
    else:
        player_id = session
    
    if not player_id:
        return
    
    state = get_player_state(player_id)
    pos = state.get('position', {'map_id': 'village', 'node_id': 'village_center'})
    p_map, p_node = pos['map_id'], pos['node_id']
    actors_here = get_actors_at_position(p_map, p_node)
    
    # First, try exact match by actor ID (e.g., "thorin_ironvein" or "seraphina")
    matched_npc_id = None
    for actor_id in actors_here:
        if actor_id.lower() == npc_id:
            matched_npc_id = actor_id
            print(f"[NPC_CHAT] Found by exact ID match: {matched_npc_id}")
            break
    
    # Second, try fuzzy matching (display names, unknown names, jobs)
    if not matched_npc_id:
        print(f"[NPC_CHAT] Trying fuzzy matching for '{npc_id}'")
        for actor_id in actors_here:
            actor_data = get_npc_data(actor_id)
            if actor_data:
                # Check against display name
                display_name = get_actor_display_name(actor_id, state).lower()
                display_clean = display_name
                if display_clean.startswith('a '):
                    display_clean = display_clean[2:]
                elif display_clean.startswith('an '):
                    display_clean = display_clean[3:]
                display_clean = display_clean.replace(' is here', '').replace(' ', '_')
                print(f"[NPC_CHAT] Checking {actor_id}: display_clean='{display_clean}'")
                if npc_id in display_clean or display_clean in npc_id or npc_id_underscore in display_clean or display_clean in npc_id_underscore:
                    matched_npc_id = actor_id
                    print(f"[NPC_CHAT] Found by display name match: {matched_npc_id}")
                    break
                # Check against unknown_name
                appearance = actor_data.get('appearance', {})
                unknown_name = appearance.get('unknown_name', '').lower()
                if unknown_name.startswith('a '):
                    unknown_name = unknown_name[2:]
                elif unknown_name.startswith('an '):
                    unknown_name = unknown_name[3:]
                unknown_name = unknown_name.replace(' is here', '').replace(' ', '_')
                if npc_id in unknown_name or unknown_name in npc_id or npc_id_underscore in unknown_name or unknown_name in npc_id_underscore:
                    matched_npc_id = actor_id
                    print(f"[NPC_CHAT] Found by unknown_name match: {matched_npc_id}")
                    break
                # Check against known_name and full_name
                known_name = appearance.get('known_name', '').lower().replace(' ', '_')
                full_name = appearance.get('full_name', '').lower().replace(' ', '_')
                if npc_id in known_name or known_name in npc_id or npc_id_underscore in known_name or known_name in npc_id_underscore or npc_id in full_name or full_name in npc_id or npc_id_underscore in full_name or full_name in npc_id_underscore:
                    matched_npc_id = actor_id
                    print(f"[NPC_CHAT] Found by known/full name match: {matched_npc_id}")
                    break
                # Check against job/role
                world_data = actor_data.get('world') or {}
                job = (world_data.get('job', '') or '').lower()
                if job and (npc_id == job or npc_id == job.replace(' ', '_') or npc_id_underscore == job or npc_id_underscore == job.replace(' ', '_')):
                    matched_npc_id = actor_id
                    print(f"[NPC_CHAT] Found by job match: {matched_npc_id}")
                    break
                conv = actor_data.get('conversation') or {}
                job = (conv.get('job', '') or '').lower()
                if job and (npc_id == job or npc_id == job.replace(' ', '_') or npc_id_underscore == job or npc_id_underscore == job.replace(' ', '_')):
                    matched_npc_id = actor_id
                    print(f"[NPC_CHAT] Found by conversation job match: {matched_npc_id}")
                    break
    
    # Last resort: try conversation memory (only if no other match found)
    if not matched_npc_id:
        player_memories = conversation_memories.get(player_id, {})
        # Find any NPC the player has talked to - but validate they're actually here
        for mem_npc_id, mem_data in player_memories.items():
            if mem_data.get('history'):
                # Player has talked to this NPC before - verify they're actually at this location
                if mem_npc_id in actors_here:
                    matched_npc_id = mem_npc_id
                    print(f"[NPC_CHAT] Found from conversation history (last resort): {matched_npc_id}")
                    break
                else:
                    print(f"[NPC_CHAT] NPC {mem_npc_id} in memory but not at current location")
    
    if not matched_npc_id:
        emit('npc_chat_response', {'lines': [f"You cannot talk to {npc_name.title()} anymore, they are not in your node."] })
        return
    
    # Check if this is the first interaction (before getting response)
    mem = conversation_memories.get(player_id, {}).get(matched_npc_id, None)
    has_met_before = mem is not None and len(mem.get('history', [])) > 0
    
    # Store the matched NPC ID in conversation memory for future reference
    if player_id not in conversation_memories:
        conversation_memories[player_id] = {}
    if matched_npc_id not in conversation_memories[player_id]:
        conversation_memories[player_id][matched_npc_id] = {
            'history': [], 'state': 'general', 'childish_warnings': 0
        }
    # Store the current conversation partner
    conversation_memories[player_id][matched_npc_id]['current_npc'] = matched_npc_id
    
    response = handle_npc_conversation(matched_npc_id, message, player_id)
    emit('npc_chat_response', {'lines': [response]})
    
    # Reveal identity AFTER first conversation exchange (not on greeting)
    if not has_met_before:
        state = get_player_state(player_id)
        reveal_actor_identity(state, matched_npc_id)
    
    # Emit updated world state so the NPC name updates immediately
    update = build_world_update_for_state(player_id, state)
    emit('world_update', update)