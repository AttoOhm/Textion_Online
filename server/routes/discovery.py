"""
Discovery routes - discovery system functions.
"""

from server.state import (
    WORLD_MAPS, player_states
)
from server.state import get_player_state, get_node
from server.state import create_event


def discover_node(state, node_id):
    """Track node discovery. Returns True if newly discovered."""
    disc = state['discovery']
    if node_id not in disc['visited_nodes']:
        disc['visited_nodes'].append(node_id)
        node = get_node(state['position']['map_id'], node_id)
        node_name = node.get('name', node_id) if node else node_id
        create_event('discovery', state['position']['map_id'], node_id,
                     ['default_player'], data={'discovery_type': 'node', 'name': node_name})
        return True
    return False


def discover_actor(state, actor_id):
    """Track actor identity discovery. Returns True if newly discovered."""
    disc = state['discovery']
    if actor_id not in disc['known_actors']:
        disc['known_actors'].append(actor_id)
        actor_data = get_npc_data(actor_id)
        actor_name = actor_data.get('name', actor_id) if actor_data else actor_id
        pos = state['position']
        create_event('discovery', pos['map_id'], pos['node_id'],
                     ['default_player', actor_id],
                     data={'discovery_type': 'actor', 'name': actor_name})
        return True
    return False


def discover_entity(state, entity_id):
    """Track world entity discovery. Returns True if newly discovered."""
    disc = state['discovery']
    if entity_id not in disc['known_entities']:
        disc['known_entities'].append(entity_id)
        pos = state['position']
        create_event('discovery', pos['map_id'], pos['node_id'],
                     ['default_player'],
                     data={'discovery_type': 'entity', 'name': entity_id})
        return True
    return False


def discover_location(state, location_id):
    """Track location discovery. Returns True if newly discovered."""
    disc = state['discovery']
    if location_id not in disc['known_locations']:
        disc['known_locations'].append(location_id)
        pos = state['position']
        create_event('discovery', pos['map_id'], pos['node_id'],
                     ['default_player'],
                     data={'discovery_type': 'location', 'name': location_id})
        return True
    return False


def is_actor_known(state, actor_id):
    """Check if player knows this actor's identity."""
    return actor_id in state['discovery']['known_actors']


def reveal_actor_identity(state, actor_id):
    """Explicitly reveal an actor's identity to the player."""
    return discover_actor(state, actor_id)


# Import get_npc_data here to avoid circular imports
from server.state import get_npc_data