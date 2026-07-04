"""
Movement routes - move command, entrance handling, schedule-based movement.
"""

from flask import request
from flask_socketio import emit
from server.state import (
    socketio, WORLD_MAPS, WORLD_ENTRANCES, ACTOR_POSITIONS,
    player_sessions, player_states, pending_commands
)
from server.state import get_player_state, get_node, get_game_hour
from server.state import log_movement, create_event
from server.state import discover_node, discover_entity, discover_location
import time


@socketio.on('command')
def handle_command(command):
    """Handle movement commands."""
    sid = request.sid
    player_id = player_sessions.get(sid, 'default_player')
    state = get_player_state(player_id)
    cmd = command.strip().lower()
    cmd_parts = cmd.split()
    base_cmd = cmd_parts[0] if cmd_parts else ''
    
    # Handle entrance commands
    full_cleaned_cmd = cmd.strip()
    is_entrance_cmd = False
    entrance_match_word = ""
    for ent_word in ['enter', 'go', 'exit to']:
        if full_cleaned_cmd == ent_word or full_cleaned_cmd.startswith(ent_word + " "):
            is_entrance_cmd = True
            entrance_match_word = ent_word
            break
    
    if base_cmd == 'move' and len(cmd_parts) > 1:
        # Queue movement command for tick processing
        if player_id not in pending_commands:
            pending_commands[player_id] = []
        pending_commands[player_id].append(command)
        emit('command_result', {'message': f'[{command}] queued.'})
    
    elif is_entrance_cmd:
        # Use entrance at current location
        pos = state.get('position', {'map_id': 'village', 'node_id': 'village_center'})
        p_map, p_node = pos['map_id'], pos['node_id']
        
        # Find entrance at this location
        entrance = None
        for ent_id, ent_data in WORLD_ENTRANCES.items():
            if ent_data.get('map_id') == p_map and ent_data.get('node_id') == p_node:
                entrance = ent_data
                break
        
        if entrance:
            expected_cmd = ent_data.get('command', 'enter').strip().lower()
            if expected_cmd != entrance_match_word:
                emit('command_result', {'error': f'You cannot {entrance_match_word} here. Try "{expected_cmd}" to use this entrance.'})
                return
            
            dest_map = entrance.get('destination_map')
            dest_node = entrance.get('destination_node')
            state['position'] = {'map_id': dest_map, 'node_id': dest_node}
            discover_node(state, dest_node)
            emit('command_result', {'message': f'You entered/exited via {entrance.get("name", "the entrance")}.'})
        else:
            emit('command_result', {'error': 'No entrance here.'})


def process_movement_command(player_id, command):
    """Process a queued movement command during tick."""
    state = get_player_state(player_id)
    cmd = command.strip().lower()
    cmd_parts = cmd.split()
    base_cmd = cmd_parts[0] if cmd_parts else ''
    
    if base_cmd == 'move' and len(cmd_parts) > 1:
        # Skip 'to' if present (e.g., "move to village center" or "move village center")
        if cmd_parts[1] == 'to' and len(cmd_parts) > 2:
            target_name = ' '.join(cmd_parts[2:]).lower().replace(' ', '_')
        else:
            target_name = ' '.join(cmd_parts[1:]).lower().replace(' ', '_')
        pos = state.get('position', {'map_id': 'village', 'node_id': 'village_center'})
        p_map, p_node = pos['map_id'], pos['node_id']
        node = get_node(p_map, p_node)
        
        if node:
            exits = node.get('exits', {})
            for exit_name, dest_node_id in exits.items():
                # Check exact match, normalized match, and with "to " prefix (for exits like "to village center")
                exit_normalized = exit_name.lower().replace(' ', '_')
                exit_with_to = f'to {exit_name}' if not exit_name.lower().startswith('to ') else exit_name.lower()
                if exit_name.lower() == target_name or exit_normalized == target_name or exit_with_to == target_name or dest_node_id.lower() == target_name:
                    state['position'] = {'map_id': p_map, 'node_id': dest_node_id}
                    # Node discovery
                    if discover_node(state, dest_node_id):
                        dest_node = get_node(p_map, dest_node_id)
                        if dest_node:
                            print(f"[DISCOVER] You discover {dest_node.get('name', dest_node_id)}.")
                    # Discover entities at the new node
                    dest_node = get_node(p_map, dest_node_id)
                    if dest_node:
                        for ent in dest_node.get('entities', []):
                            discover_entity(state, ent)
                        # Legitimate location discovery
                        discover_location(state, dest_node_id)
                    log_movement(p_map, dest_node_id, player_id,
                                 from_map_id=p_map, from_node_id=p_node)
                    break