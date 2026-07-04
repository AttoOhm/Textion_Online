"""
Chat routes - say command and chat broadcasting.
"""

from flask import request
from flask_socketio import emit
from server.state import (
    socketio, player_sessions, player_states
)
from server.state import get_player_state


@socketio.on('command')
def handle_command(command):
    """Handle chat commands."""
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
    cmd = command.strip().lower()
    
    if cmd.startswith('say ') and len(cmd) > 4:
        # Local chat - broadcast to all players in same node
        message = cmd[4:].strip()
        if not message:
            emit('command_result', {'error': 'Say what?'})
            return
        
        pos = state.get('position', {'map_id': 'village', 'node_id': 'village_center'})
        p_map, p_node = pos['map_id'], pos['node_id']
        
        # Get player display name
        player_name = player_id.replace('player_', 'Player ')
        
        # Broadcast to all players in the same node
        for other_pid, other_state in player_states.items():
            other_pos = other_state.get('position', {})
            if other_pos.get('map_id') == p_map and other_pos.get('node_id') == p_node:
                # Emit to specific player's session
                for sid, pid in player_sessions.items():
                    if pid == other_pid:
                        socketio.emit('chat_message', {
                            'from': player_name,
                            'message': message,
                            'type': 'local'
                        }, room=sid)
                        break
        
        emit('command_result', {'message': f"You say: \"{message}\""})