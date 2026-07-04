"""
Player routes - connection handling, session management, player state.
"""

import os
import json
from flask import request
from flask_socketio import emit
from server.state import (
    socketio, player_sessions, player_states,
    create_default_attributes, ACTOR_POSITIONS, save_player_state, tick_number
)

PLAYERS_DIR = os.path.join('data', 'players')
os.makedirs(PLAYERS_DIR, exist_ok=True)


@socketio.on('connect')
def handle_connect():
    """Handle new player connection."""
    global player_sessions, player_states
    sid = request.sid
    # Player ID will be set when character is selected (login_character)
    # For now, just store the session
    player_sessions[sid] = {'player_id': None}
    # CRITICAL: Clean up stale sessions that may reference a dead socket
    # This handles the case where handle_disconnect didn't fire before reconnection
    # (e.g., browser page refresh where old socket is still in player_sessions)
    stale_sids = []
    for existing_sid, existing_session in list(player_sessions.items()):
        if existing_sid == sid:
            continue  # Skip current socket
        existing_pid = existing_session.get('player_id') if isinstance(existing_session, dict) else existing_session
        # If this existing session has no player_id, and it's not the current sid, it's stale
        if not existing_pid and existing_sid != sid:
            stale_sids.append(existing_sid)
    for stale_sid in stale_sids:
        del player_sessions[stale_sid]
        if stale_sids:
            print(f"[CONNECT] Cleaned up {len(stale_sids)} stale anonymous sessions")
    # Check if there's a disconnected player we can reuse (reconnection grace period)
    from server.state import tick_number
    RECONNECT_GRACE_TICKS = 6
    reused_player_id = None
    for pid, state in list(player_states.items()):
        if state.get('_disconnected') and state.get('_disconnect_tick'):
            ticks_ago = tick_number - state['_disconnect_tick']
            if ticks_ago <= RECONNECT_GRACE_TICKS:
                # Found a recently disconnected player - reuse this slot
                reused_player_id = pid
                # Clear disconnect markers and preserve account info
                account_id = state.pop('_account_id', '')
                character_name = state.pop('_character_name', '')
                state.pop('_disconnected', None)
                state.pop('_disconnect_tick', None)
                # CRITICAL: Remove any stale session entries for this player_id
                # to prevent ticker from emitting to old/dead sockets
                stale_pid_sids = []
                for existing_sid, existing_session in list(player_sessions.items()):
                    if existing_sid == sid:
                        continue  # Skip current sid
                    existing_pid = existing_session.get('player_id') if isinstance(existing_session, dict) else existing_session
                    if existing_pid == pid:
                        stale_pid_sids.append(existing_sid)
                for stale_pid_sid in stale_pid_sids:
                    del player_sessions[stale_pid_sid]
                    if stale_pid_sids:
                        print(f"[CONNECT] Removed {len(stale_pid_sids)} stale session(s) for player {pid}")
                # Update session to point to the reused player_id, preserving account info
                player_sessions[sid] = {
                    'player_id': pid,
                    'account_id': account_id,
                    'character_name': character_name
                }
                print(f"[CONNECT] Reusing player slot {pid} for client {sid} (disconnected {ticks_ago} ticks ago)")
                break
    # Initialize player state if new (character data loaded later via login_character)
    if not reused_player_id:
        print(f"[CONNECT] Client {sid} -> waiting for character selection")
    else:
        print(f"[CONNECT] Client {sid} -> reused {reused_player_id}")
    # Send welcome message to the newly connected client
    if socketio:
        socketio.emit('command_result', {'message': 'Welcome to Texttion Online!'}, room=sid)


def _init_default_state(player_id):
    """Initialize a fresh default player state."""
    global player_states
    if player_id not in player_states:
        player_states[player_id] = {
            'name': player_id,
            'position': {'map_id': 'village', 'node_id': 'village_center'},
            'hp': 100, 'max_hp': 100, 'coins': 100,
            'inventory': [], 'equipment': {'weapon': None, 'armor': None, 'accessory': None},
            'skills': {}, 'quests': [], 'quest_notes': {}, 'journal': [], 'completed_quests': [],
            'discovery': {
                'visited_nodes': [],
                'known_actors': [],
                'known_entities': [],
                'known_locations': [],
                'location_positions': [],
            },
            'attributes': create_default_attributes(),
            'disciplines': {},
            'techniques': {},
            'reputation': {'actors': {}, 'factions': {}}
        }


@socketio.on('disconnect')
def handle_disconnect(sid):
    """Handle player disconnection."""
    global player_sessions, player_states, ACTOR_POSITIONS
    session = player_sessions.get(sid)
    if session:
        if isinstance(session, dict):
            player_id = session.get('player_id')
            account_id = session.get('account_id', '')
            character_name = session.get('character_name', '')
        else:
            player_id = session
            account_id = ''
            character_name = ''
        print(f"[DISCONNECT] Client {sid} ({player_id}) disconnected")
        # Save player state before removing
        if player_id:
            save_player_state(player_id)
        # Remove from sessions
        del player_sessions[sid]
        # Keep the state for reconnection grace period (6 ticks = 2 minutes)
        # Mark as disconnected but don't delete
        if player_id and player_id in player_states:
            state = player_states[player_id]
            state['_disconnected'] = True
            state['_account_id'] = account_id
            state['_character_name'] = character_name
            from server.state import tick_number as current_tick
            state['_disconnect_tick'] = current_tick
            # Keep in ACTOR_POSITIONS so other players still see them
            return
    else:
        print(f"[DISCONNECT] Client {sid} disconnected (no session)")