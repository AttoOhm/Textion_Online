"""
Inventory routes - inventory command and get_inventory handler.
"""

from flask import request
from server.state import (
    socketio, player_sessions, player_states
)
from server.state import get_player_state
from server.state import _items_db
from engine.items import is_stackable, get_item_name


def build_inventory_data(player_id):
    """Build inventory data dict for a player. Returns dict or None if player not found."""
    state = get_player_state(player_id)
    if not state:
        return None
    equipment = state.get('equipment', {})
    inventory_items = []

    for item_entry in state.get('inventory', []):
        if isinstance(item_entry, dict) and 'item_id' in item_entry:
            item_id = item_entry['item_id']
            quantity = item_entry.get('quantity', 1)
            item_name = get_item_name(item_id)
            if is_stackable(item_id) and quantity > 1:
                inventory_items.append(f"{item_name} (x{quantity})")
            else:
                inventory_items.append(item_name)
        else:
            item_name = item_entry.get('name', item_entry) if isinstance(item_entry, dict) else item_entry
            inventory_items.append(item_name)

    # Add equipped items with friendly slot labels
    for slot, item_entry in equipment.items():
        if item_entry:
            item_name = item_entry.get('name', item_entry) if isinstance(item_entry, dict) else item_entry
            inventory_items.append(f"{item_name} (equipped {slot.replace('_', ' ')})")

    return {
        'items': inventory_items,
        'coins': state.get('coins', 0),
        'equipment': {
            'main_hand': equipment.get('main_hand'),
            'off_hand': equipment.get('off_hand'),
            'armor': equipment.get('armor'),
            'necklace_1': equipment.get('necklace_1'),
            'necklace_2': equipment.get('necklace_2'),
            'bracelet_1': equipment.get('bracelet_1'),
            'bracelet_2': equipment.get('bracelet_2'),
            'bracelet_3': equipment.get('bracelet_3'),
            'bracelet_4': equipment.get('bracelet_4'),
            'ring_1': equipment.get('ring_1'),
            'ring_2': equipment.get('ring_2'),
            'ring_3': equipment.get('ring_3'),
            'ring_4': equipment.get('ring_4'),
            'ring_5': equipment.get('ring_5'),
            'ring_6': equipment.get('ring_6'),
            'ring_7': equipment.get('ring_7'),
            'ring_8': equipment.get('ring_8')
        }
    }


@socketio.on('get_inventory')
def handle_get_inventory():
    """Handle inventory request."""
    sid = request.sid
    session = player_sessions.get(sid)
    if isinstance(session, dict):
        player_id = session.get('player_id', 'default_player')
    else:
        player_id = session if session else 'default_player'
    data = build_inventory_data(player_id)
    if data:
        socketio.emit('inventory_data', data, room=sid)


def emit_inventory_update(player_id, sid=None):
    """Emit inventory_data for a player, optionally to a specific sid.
    Uses socketio.emit directly so it works from background threads."""
    data = build_inventory_data(player_id)
    if not data:
        return
    if sid:
        socketio.emit('inventory_data', data, room=sid)
    else:
        socketio.emit('inventory_data', data)
