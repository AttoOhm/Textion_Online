"""
Quest routes - quest handlers, quest acceptance/completion.
"""

from flask import request
from flask_socketio import emit
from server.state import (
    socketio, player_sessions, player_states
)
from server.state import get_player_state, get_quest_data
from server.state import _quest_cache, conversation_memories
from server.state import apply_quest_reputation_rewards
from server.state import log_quest_accept, log_quest_complete


@socketio.on('get_quests')
def handle_get_quests():
    """Handle quest book request."""
    sid = request.sid
    session = player_sessions.get(sid)
    
    # Handle both old format (string) and new format (dict with account_id/player_id)
    if isinstance(session, dict):
        player_id = session.get('player_id')
    else:
        player_id = session
    
    if not player_id:
        emit('quest_data', {'error': 'No character selected'})
        return
    
    state = get_player_state(player_id)
    emit('quest_data', {
        'active': [q for q in state.get('quests', []) if q.get('status') == 'active'],
        'completed': state.get('completed_quests', []),
        'notes': state.get('quest_notes', {})
    })


@socketio.on('save_quest_note')
def handle_save_quest_note(data):
    """Handle quest note saving."""
    sid = request.sid
    player_id = player_sessions.get(sid, 'default_player')
    state = get_player_state(player_id)
    quest_id = data.get('questId', '')
    note = data.get('note', '')
    if quest_id:
        state.setdefault('quest_notes', {})[quest_id] = note
        emit('note_saved', {'success': True})


def accept_quest_for_player(player_id, quest_id, quest_data):
    """Accept a quest for a player."""
    state = get_player_state(player_id)
    q_name = quest_data.get('name', 'Unknown Quest')
    
    state.setdefault('quests', []).append({
        'id': quest_id,
        'name': q_name,
        'description': quest_data.get('description', ''),
        'status': 'active',
        'steps': quest_data.get('steps', [])
    })
    state.setdefault('quest_notes', {})[quest_id] = ''
    
    # Log quest acceptance
    pos = state.get('position', {'map_id': 'village', 'node_id': 'village_center'})
    log_quest_accept(pos['map_id'], pos['node_id'], player_id, quest_id, q_name)
    
    return q_name


def complete_quest_for_player(player_id, quest_id, quest_data):
    """Complete a quest for a player."""
    state = get_player_state(player_id)
    q_name = quest_data.get('name', 'Unknown Quest')
    rewards = quest_data.get('rewards', {})
    
    # Move quest from active to completed
    state['quests'] = [q for q in state.get('quests', []) if q.get('id') != quest_id]
    state.setdefault('completed_quests', []).append({
        'id': quest_id,
        'name': q_name,
        'completed_at': 'now'
    })
    
    # Grant rewards
    if rewards.get('gold'):
        state['coins'] = state.get('coins', 0) + rewards['gold']
    
    # Apply reputation rewards
    apply_quest_reputation_rewards(state, quest_data)
    
    # Log quest completion
    pos = state.get('position', {'map_id': 'village', 'node_id': 'village_center'})
    log_quest_complete(pos['map_id'], pos['node_id'], player_id, quest_id, q_name)
    
    return rewards