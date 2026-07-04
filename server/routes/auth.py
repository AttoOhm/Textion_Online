"""
Authentication routes - account system and character management.
"""

import os
import json
import hashlib
from flask import request
from flask_socketio import emit
from server.state import (
    socketio, player_sessions, player_states, ACTOR_POSITIONS
)
from server.state import get_player_state, create_default_attributes

# Directories
ACCOUNTS_DIR = os.path.join('data', 'accounts')
PLAYERS_DIR = os.path.join('data', 'players')
os.makedirs(ACCOUNTS_DIR, exist_ok=True)
os.makedirs(PLAYERS_DIR, exist_ok=True)

MAX_CHARACTERS_PER_ACCOUNT = 4


def hash_password(password):
    """Hash password for storage."""
    return hashlib.sha256(password.encode()).hexdigest()


@socketio.on('create_account')
def handle_create_account(data):
    """Create a new account."""
    account_id = data.get('account_id', '').strip().lower()
    password = data.get('password', '')

    if not account_id or not password:
        emit('account_created', {'success': False, 'error': 'Account ID and password required'})
        return

    if len(account_id) < 3 or len(account_id) > 20:
        emit('account_created', {'success': False, 'error': 'Account ID must be 3-20 characters'})
        return

    if len(password) < 4:
        emit('account_created', {'success': False, 'error': 'Password must be at least 4 characters'})
        return

    filepath = os.path.join(ACCOUNTS_DIR, f"{account_id}.json")

    if os.path.exists(filepath):
        emit('account_created', {'success': False, 'error': 'Account already exists'})
        return

    account_data = {
        'account_id': account_id,
        'password_hash': hash_password(password),
        'characters': []
    }

    try:
        with open(filepath, 'w') as f:
            json.dump(account_data, f, indent=2)

        emit('account_created', {'success': True, 'account_id': account_id})
    except Exception as e:
        emit('account_created', {'success': False, 'error': f'Failed to create account: {str(e)}'})


@socketio.on('login_account')
def handle_login_account(data):
    """Login to existing account."""
    account_id = data.get('account_id', '').strip().lower()
    password = data.get('password', '')

    if not account_id or not password:
        emit('account_logged_in', {'success': False, 'error': 'Account ID and password required'})
        return

    filepath = os.path.join(ACCOUNTS_DIR, f"{account_id}.json")

    if not os.path.exists(filepath):
        emit('account_logged_in', {'success': False, 'error': 'Account not found'})
        return

    try:
        with open(filepath, 'r') as f:
            account_data = json.load(f)

        if account_data.get('password_hash') != hash_password(password):
            emit('account_logged_in', {'success': False, 'error': 'Invalid password'})
            return

        # Update character locations from their actual player state files
        updated_characters = []
        for char_entry in account_data.get('characters', []):
            char_name = char_entry.get('name', '')
            safe_name = char_name.lower().replace(' ', '_')
            player_filepath = os.path.join(PLAYERS_DIR, f"{safe_name}.json")
            current_location_short = char_entry.get('location', 'unknown')
            try:
                if os.path.exists(player_filepath):
                    with open(player_filepath, 'r') as pf:
                        player_data = json.load(pf)
                    pos = player_data.get('position', {})
                    pos_node = pos.get('node_id', '')
                    if pos_node:
                        # Try to get the display name from the map data
                        pos_map = pos.get('map_id', 'village')
                        from server.state import WORLD_MAPS
                        map_data = WORLD_MAPS.get(pos_map, {})
                        node_data = map_data.get('nodes', {}).get(pos_node, {})
                        if node_data and node_data.get('name'):
                            current_location_short = node_data['name']
                        else:
                            current_location_short = pos_node.replace('_', ' ').title()
            except:
                pass  # Fall back to stored location
            updated_characters.append({
                'name': char_name,
                'location': current_location_short
            })

        # Store account_id in session (preserve existing player_id if present)
        sid = request.sid
        existing = player_sessions.get(sid, {})
        if not isinstance(existing, dict):
            existing = {}
        existing['account_id'] = account_id
        existing.setdefault('player_id', None)
        player_sessions[sid] = existing

        emit('account_logged_in', {
            'success': True,
            'account_id': account_id,
            'characters': updated_characters
        })
    except Exception as e:
        emit('account_logged_in', {'success': False, 'error': f'Failed to login: {str(e)}'})


@socketio.on('create_character')
def handle_create_character(data):
    """Create a new character for logged-in account."""
    sid = request.sid
    session = player_sessions.get(sid)

    if not session or not isinstance(session, dict):
        emit('character_created', {'success': False, 'error': 'Not logged in to account', 'debug': f'session={session}, sid={sid}'})
        return

    account_id = session.get('account_id')
    if not account_id:
        emit('character_created', {'success': False, 'error': 'Not logged in to account', 'debug': f'account_id missing from session: {session}'})
        return

    name = data.get('name', '').strip()
    attributes = data.get('attributes', {})

    if not name:
        emit('character_created', {'success': False, 'error': 'Name cannot be empty'})
        return

    safe_name = name.lower().replace(' ', '_')
    char_filepath = os.path.join(PLAYERS_DIR, f"{safe_name}.json")
    account_filepath = os.path.join(ACCOUNTS_DIR, f"{account_id}.json")

    # Check if character name already exists
    if os.path.exists(char_filepath):
        emit('character_created', {'success': False, 'error': 'Character name already taken'})
        return

    # Check character limit
    try:
        with open(account_filepath, 'r') as f:
            account_data = json.load(f)

        if len(account_data.get('characters', [])) >= MAX_CHARACTERS_PER_ACCOUNT:
            emit('character_created', {'success': False, 'error': f'Maximum {MAX_CHARACTERS_PER_ACCOUNT} characters per account'})
            return
    except:
        emit('character_created', {'success': False, 'error': 'Failed to read account data'})
        return

    # Validate attributes
    total_points = sum(attributes.values())
    if total_points != 140:
        emit('character_created', {'success': False, 'error': f'Must distribute exactly 140 points (used: {total_points})'})
        return

    for attr, value in attributes.items():
        if value < 5:
            emit('character_created', {'success': False, 'error': f'{attr} must be at least 5'})
            return
        if value > 30:
            emit('character_created', {'success': False, 'error': f'{attr} cannot exceed 30'})
            return

    # Create character data
    character_data = {
        'name': name,
        'attributes': attributes,
        'position': {'map_id': 'village', 'node_id': 'village_center'},
        'hp': 100,
        'max_hp': 100,
        'coins': 100,
        'inventory': [],
        'equipment': {'weapon': None, 'armor': None, 'accessory': None},
        'skills': {},
        'quests': [],
        'quest_notes': {},
        'journal': [],
        'completed_quests': [],
        'discovery': {
            'visited_nodes': [],
            'known_actors': [],
            'known_entities': [],
            'known_locations': [],
            'location_positions': [],
        },
        'reputation': {'actors': {}, 'factions': {}}
    }

    try:
        # Save character file
        with open(char_filepath, 'w') as f:
            json.dump(character_data, f, indent=2)

        # Update account with new character
        account_data['characters'].append({
            'name': name,
            'location': 'village_center'
        })

        with open(account_filepath, 'w') as f:
            json.dump(account_data, f, indent=2)

        # Auto-login the character - use character name as player_id
        player_id = safe_name
        session['player_id'] = player_id
        session['character_name'] = name

        if player_id not in player_states:
            player_states[player_id] = character_data
        else:
            player_states[player_id].update(character_data)

        # Add player to actor positions
        pos = character_data.get('position', {'map_id': 'village', 'node_id': 'village_center'})
        ACTOR_POSITIONS[player_id] = pos

        emit('character_created', {
            'success': True,
            'player_id': player_id,
            'character_name': name
        })
    except Exception as e:
        import traceback
        error_detail = f'{str(e)}\n{traceback.format_exc()}'
        emit('character_created', {'success': False, 'error': f'Failed to create character: {error_detail}'})


@socketio.on('login_character')
def handle_login_character(data):
    """Login with existing character."""
    sid = request.sid
    session = player_sessions.get(sid)

    if not session or not isinstance(session, dict):
        emit('character_logged_in', {'success': False, 'error': 'Not logged in to account'})
        return

    account_id = session.get('account_id')
    if not account_id:
        emit('character_logged_in', {'success': False, 'error': 'Not logged in to account'})
        return

    name = data.get('name', '').strip()

    if not name:
        emit('character_logged_in', {'success': False, 'error': 'Name cannot be empty'})
        return

    safe_name = name.lower().replace(' ', '_')
    filepath = os.path.join(PLAYERS_DIR, f"{safe_name}.json")

    if not os.path.exists(filepath):
        emit('character_logged_in', {'success': False, 'error': 'Character not found'})
        return

    try:
        with open(filepath, 'r') as f:
            character_data = json.load(f)

        # Strip legacy and private fields that should not persist from disk
        for key in ['stats', '_disconnected', '_disconnect_tick', '_account_id', '_character_name']:
            character_data.pop(key, None)

        # Auto-login the character - use character name as player_id
        player_id = safe_name
        session['player_id'] = player_id
        session['character_name'] = name
        session['account_id'] = account_id

        if player_id not in player_states:
            player_states[player_id] = character_data
        else:
            player_states[player_id].update(character_data)

        # Store account_id in player state for future reconnections
        player_states[player_id]['account_id'] = account_id

        # CRITICAL: Clear all private markers so ticker doesn't skip this player
        for key in ['_disconnected', '_disconnect_tick', '_account_id', '_character_name']:
            player_states[player_id].pop(key, None)

        # Add player to actor positions
        pos = character_data.get('position', {'map_id': 'village', 'node_id': 'village_center'})
        ACTOR_POSITIONS[player_id] = pos

        emit('character_logged_in', {
            'success': True,
            'player_id': player_id,
            'character_name': name,
            'character_data': character_data
        })
    except Exception as e:
        emit('character_logged_in', {'success': False, 'error': f'Failed to load character: {str(e)}'})


@socketio.on('delete_character')
def handle_delete_character(data):
    """Delete a character."""
    sid = request.sid
    session = player_sessions.get(sid)

    if not session or not isinstance(session, dict):
        emit('character_deleted', {'success': False, 'error': 'Not logged in to account'})
        return

    account_id = session.get('account_id')
    if not account_id:
        emit('character_deleted', {'success': False, 'error': 'Not logged in to account'})
        return

    name = data.get('name', '').strip()

    if not name:
        emit('character_deleted', {'success': False, 'error': 'Name cannot be empty'})
        return

    safe_name = name.lower().replace(' ', '_')
    char_filepath = os.path.join(PLAYERS_DIR, f"{safe_name}.json")
    account_filepath = os.path.join(ACCOUNTS_DIR, f"{account_id}.json")

    try:
        # Delete character file
        if os.path.exists(char_filepath):
            os.remove(char_filepath)

        # Update account
        with open(account_filepath, 'r') as f:
            account_data = json.load(f)

        account_data['characters'] = [c for c in account_data.get('characters', []) if c.get('name') != name]

        with open(account_filepath, 'w') as f:
            json.dump(account_data, f, indent=2)

        emit('character_deleted', {'success': True, 'name': name})
    except Exception as e:
        emit('character_deleted', {'success': False, 'error': str(e)})


@socketio.on('save_character')
def handle_save_character():
    """Save current character progress."""
    sid = request.sid
    session = player_sessions.get(sid)

    if not session or not isinstance(session, dict):
        emit('character_saved', {'success': False, 'error': 'Not logged in'})
        return

    player_id = session.get('player_id')
    if not player_id:
        emit('character_saved', {'success': False, 'error': 'No character selected'})
        return

    state = get_player_state(player_id)
    # Use character_name from session for correct file name
    character_name = session.get('character_name', state.get('name', player_id))
    safe_name = character_name.lower().replace(' ', '_')
    filepath = os.path.join(PLAYERS_DIR, f"{safe_name}.json")

    try:
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        emit('character_saved', {'success': True})
    except Exception as e:
        emit('character_saved', {'success': False, 'error': str(e)})