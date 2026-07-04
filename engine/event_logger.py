"""
Event Logger - Runtime event storage for world simulation.

Events are generated from gameplay actions and stored in memory during runtime.
This module provides logging only; no gameplay logic depends on it yet.

Event Types:
  - conversation: NPC dialogue interaction
  - movement: player or NPC position change
  - quest_accept: player accepts a quest
  - quest_complete: player completes a quest
  - discovery: (reserved) player discovers new location/object
  - item_transfer: (reserved) item changes hands
  - combat: (reserved) combat encounter
"""

import time
import uuid
import threading


# Global event log (in-memory during runtime)
_event_log = []
_lock = threading.Lock()


# Canonical event types (only these are valid)
VALID_EVENT_TYPES = frozenset([
    'conversation',
    'movement',
    'quest_accept',
    'quest_complete',
    'discovery',
    'item_transfer',
    'combat',
])


def create_event(event_type, map_id, node_id, participants, data=None):
    """Create a canonical event and append it to the log.

    Args:
        event_type: One of VALID_EVENT_TYPES.
        map_id: The map where the event occurred.
        node_id: The node where the event occurred.
        participants: List of participant identifiers (player_id, npc_id, etc.).
        data: Optional dict of additional event-specific data.

    Returns:
        The created event dict.
    """
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event_type: {event_type}. Must be one of {VALID_EVENT_TYPES}")

    event = {
        'event_id': str(uuid.uuid4())[:8],
        'event_type': event_type,
        'timestamp': time.time(),
        'map_id': map_id,
        'node_id': node_id,
        'participants': list(participants),
        'data': data or {},
    }

    with _lock:
        _event_log.append(event)

    return event


def log_conversation(map_id, node_id, player_id, npc_id, summary=None):
    """Log an NPC conversation event."""
    return create_event('conversation', map_id, node_id, [player_id, npc_id],
                        data={'summary': summary or ''})


def log_movement(map_id, node_id, participant_id, from_map_id=None, from_node_id=None):
    """Log a movement event."""
    return create_event('movement', map_id, node_id, [participant_id],
                        data={'from_map_id': from_map_id, 'from_node_id': from_node_id})


def log_quest_accept(map_id, node_id, player_id, quest_id, quest_name=None):
    """Log a quest acceptance event."""
    return create_event('quest_accept', map_id, node_id, [player_id],
                        data={'quest_id': quest_id, 'quest_name': quest_name or quest_id})


def log_quest_complete(map_id, node_id, player_id, quest_id, quest_name=None):
    """Log a quest completion event."""
    return create_event('quest_complete', map_id, node_id, [player_id],
                        data={'quest_id': quest_id, 'quest_name': quest_name or quest_id})


def get_events(event_type=None, map_id=None, node_id=None, participant=None, limit=None):
    """Query events from the log.

    All filters are optional. When provided, only matching events are returned.
    """
    with _lock:
        events = list(_event_log)

    if event_type:
        events = [e for e in events if e['event_type'] == event_type]
    if map_id:
        events = [e for e in events if e['map_id'] == map_id]
    if node_id:
        events = [e for e in events if e['node_id'] == node_id]
    if participant:
        events = [e for e in events if participant in e['participants']]

    if limit:
        events = events[-limit:]

    return events


def get_event_count():
    """Return total number of events in the log."""
    with _lock:
        return len(_event_log)


def clear_events():
    """Clear the event log. Useful for testing."""
    with _lock:
        _event_log.clear()