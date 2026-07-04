"""
Reputation routes - reputation system handlers.
"""

from flask import request
from flask_socketio import emit
from server.state import (
    socketio, player_sessions, player_states
)
from server.state import get_player_state
from server.state import get_actor_reputation, modify_actor_reputation
from server.state import get_faction_reputation, modify_faction_reputation
from server.state import get_reputation_label


@socketio.on('get_reputation')
def handle_get_reputation():
    """Handle reputation request."""
    sid = request.sid
    player_id = player_sessions.get(sid, 'default_player')
    state = get_player_state(player_id)
    
    reputation_data = state.get('reputation', {'actors': {}, 'factions': {}})
    
    # Format for display
    actor_reps = []
    for actor_id, rep_value in reputation_data.get('actors', {}).items():
        label = get_reputation_label(rep_value)
        actor_reps.append({
            'actor_id': actor_id,
            'value': rep_value,
            'label': label
        })
    
    faction_reps = []
    for faction_id, rep_value in reputation_data.get('factions', {}).items():
        label = get_reputation_label(rep_value)
        faction_reps.append({
            'faction_id': faction_id,
            'value': rep_value,
            'label': label
        })
    
    emit('reputation_data', {
        'actors': actor_reps,
        'factions': faction_reps
    })