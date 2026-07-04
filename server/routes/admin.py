"""
Admin routes - admin/debug functions.
"""

from flask import request
from flask_socketio import emit
from server.state import (
    socketio, player_sessions, player_states
)
from server.state import get_player_state, tick_number, get_game_time
from server.state import WORLD_MAPS, ACTOR_POSITIONS, corpses, creature_death_times
from server.state import CREATURE_INSTANCES, player_states


@socketio.on('admin_tick')
def handle_admin_tick():
    """Manually trigger a tick (admin/debug)."""
    emit('command_result', {'message': f'Tick {tick_number} processed. Time: {get_game_time()}'})


@socketio.on('admin_status')
def handle_admin_status():
    """Get server status (admin/debug)."""
    status = {
        'tick': tick_number,
        'time': get_game_time(),
        'players_connected': len(player_sessions),
        'players_total': len(player_states),
        'actors_spawned': len(ACTOR_POSITIONS),
        'corpses': len(corpses),
        'creatures_respawning': len(creature_death_times),
        'creature_instances': len(CREATURE_INSTANCES)
    }
    emit('admin_status_data', status)


@socketio.on('admin_respawn')
def handle_admin_respawn(data):
    """Force respawn a creature (admin/debug)."""
    creature_id = data.get('creature_id', '')
    if creature_id in creature_death_times:
        del creature_death_times[creature_id]
        # Find spawn point
        instance_data = CREATURE_INSTANCES.get(creature_id, {})
        spawn_point = instance_data.get('spawn_point', {})
        map_id = spawn_point.get('map_id')
        node_id = spawn_point.get('node_id')
        if map_id and node_id:
            ACTOR_POSITIONS[creature_id] = {'map_id': map_id, 'node_id': node_id}
            emit('command_result', {'message': f'Respawned {creature_id} at {map_id}/{node_id}'})
        else:
            emit('command_result', {'error': f'No spawn point for {creature_id}'})
    else:
        emit('command_result', {'error': f'{creature_id} is not dead'})