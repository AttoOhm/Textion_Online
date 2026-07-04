"""
Chronicle - Permanent world history of important events.

Chronicle is NOT NPC memory.
Chronicle is NOT rumors.
Chronicle is NOT reputation.

Chronicle is only a curated, permanent world history.

EVENT FLOW:
  Game Event -> Event Logger -> Chronicle Filter -> Chronicle Entry

Only significant events become Chronicle entries.

CHRONICLE ENTRY FORMAT:
  {
    "id": "chr_001",
    "tick": 123,
    "event_type": "quest_accept",
    "actors": ["player", "aldric"],
    "map_id": "village",
    "node_id": "village_center",
    "summary": "Player accepted Patrol the Perimeter from Aldric."
  }

Chronicle entries are immutable.
Never edit past entries. Only append.
"""

import os
import json
import time
import uuid
import threading


# Chronicle storage directory
CHRONICLE_DIR = os.path.join('data', 'chronicle')
CHRONICLE_FILE = os.path.join(CHRONICLE_DIR, 'chronicle.jsonl')

# In-memory cache of Chronicle entries
_chronicle = []
_lock = threading.Lock()
_last_processed_event_index = -1  # Track which events have been consumed


# ============ IMPORTANT EVENT TYPES ============
# These event types are eligible to become Chronicle entries.
# Movement, schedule movement, ordinary conversation, look commands,
# and repeated discoveries are NOT recorded.
CHRONICLE_EVENT_TYPES = frozenset([
    'quest_accept',
    'quest_complete',
    'discovery',
])


# ============ HELPER FUNCTIONS ============

def _get_next_id():
    """Generate a short unique Chronicle entry ID."""
    return 'chr_' + str(uuid.uuid4())[:8]


def _ensure_chronicle_dir():
    """Ensure the Chronicle storage directory exists."""
    os.makedirs(CHRONICLE_DIR, exist_ok=True)


def _load_chronicle():
    """Load Chronicle entries from the JSONL file into memory."""
    global _chronicle
    _chronicle = []
    _ensure_chronicle_dir()
    if os.path.exists(CHRONICLE_FILE):
        with open(CHRONICLE_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        _chronicle.append(entry)
                    except json.JSONDecodeError:
                        print(f"[CHRONICLE] Warning: Failed to parse JSONL line: {line[:80]}")
    print(f"[CHRONICLE] Loaded {len(_chronicle)} entries from {CHRONICLE_FILE}")


def _append_to_file(entry):
    """Append a single Chronicle entry to the JSONL file.
    
    Uses append mode so entries are never overwritten.
    """
    _ensure_chronicle_dir()
    with open(CHRONICLE_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, sort_keys=True) + '\n')


# ============ CHRONICLE FILTER ============

def _event_is_significant(event, existing_chronicle):
    """Determine if an event should become a Chronicle entry.
    
    Filtering rules:
    - quest_accept: Always recorded
    - quest_complete: Always recorded
    - discovery: Recorded only for FIRST discovery of each type+name combination.
      Repeated discoveries (revisiting same node, rediscovering same actor) are NOT recorded.
    
    Returns True if the event should become a Chronicle entry.
    """
    event_type = event.get('event_type')
    
    # quest_accept and quest_complete are always significant
    if event_type in ('quest_accept', 'quest_complete'):
        return True
    
    # discovery: only record significant first-time discoveries
    if event_type == 'discovery':
        discovery_data = event.get('data', {})
        discovery_type = discovery_data.get('discovery_type', '')
        discovery_name = discovery_data.get('name', '')
        
        # Only record discovery events that have a clear type and name
        if not discovery_type or not discovery_name:
            return False
        
        # Significant discovery types: node, actor, location
        if discovery_type not in ('node', 'actor', 'location'):
            return False
        
        # Check if this exact discovery has been recorded before
        for entry in existing_chronicle:
            if entry.get('event_type') == 'discovery':
                entry_data = entry.get('data', {})
                if (entry_data.get('discovery_type') == discovery_type and 
                    entry_data.get('name') == discovery_name):
                    return False  # Already recorded, skip duplicate
        
        return True  # New unique discovery
    
    # All other event types are not recorded
    return False


def _build_summary(event):
    """Build a human-readable summary for a Chronicle entry.
    
    Args:
        event: The raw event dict from the event logger.
    
    Returns:
        A string summary of the event.
    """
    event_type = event.get('event_type')
    data = event.get('data', {})
    participants = event.get('participants', [])
    
    if event_type == 'quest_accept':
        quest_name = data.get('quest_name', 'Unknown Quest')
        giver = participants[1] if len(participants) > 1 else 'someone'
        return f"Player accepted {quest_name} from {giver}."
    
    elif event_type == 'quest_complete':
        quest_name = data.get('quest_name', 'Unknown Quest')
        return f"Player completed {quest_name}."
    
    elif event_type == 'discovery':
        discovery_type = data.get('discovery_type', '')
        name = data.get('name', '')
        
        if discovery_type == 'node':
            return f"Player discovered {name}."
        elif discovery_type == 'actor':
            return f"Player met {name}."
        elif discovery_type == 'location':
            # Look up the node's display name for better readability
            # name is a node_id; try to find its display name in WORLD_MAPS
            event_map_id = event.get('map_id', '')
            from server.api import get_node
            node = get_node(event_map_id, name)
            if node:
                display_name = node.get('name', name)
            else:
                display_name = name
            return f"Player discovered {display_name}."
        else:
            return f"Player discovered {name} ({discovery_type})."
    
    return f"Unknown event: {event_type}"


# ============ CHRONICLE CONSUMER ============

def _consume_events(event_log):
    """Centralized Chronicle consumer.
    
    Reads newly created events from the event log and decides whether they
    belong in the Chronicle. Only significant events are recorded.
    
    This is the ONLY place Chronicle entries are created. Do NOT scatter
    Chronicle creation throughout gameplay systems.
    
    Args:
        event_log: List of raw event dicts from the event logger.
    
    Returns:
        Number of new Chronicle entries created.
    """
    global _last_processed_event_index
    
    entries_created = 0
    
    with _lock:
        existing = list(_chronicle)
    
    # Process only new events
    start_index = _last_processed_event_index + 1
    new_events = event_log[start_index:]
    
    for event in new_events:
        if _event_is_significant(event, existing):
            entry = {
                'id': _get_next_id(),
                'tick': event.get('tick', 0),
                'event_type': event.get('event_type'),
                'actors': event.get('participants', []),
                'map_id': event.get('map_id', ''),
                'node_id': event.get('node_id', ''),
                'timestamp': event.get('timestamp', time.time()),
                'summary': _build_summary(event),
                'data': event.get('data', {}),
            }
            
            with _lock:
                _chronicle.append(entry)
            
            # Persist immediately (append to file)
            _append_to_file(entry)
            
            existing.append(entry)
            entries_created += 1
    
    # Update the last processed index
    _last_processed_event_index = len(event_log) - 1
    
    return entries_created


# ============ CHRONICLE API ============

def initialize_chronicle():
    """Initialize the Chronicle system.
    
    Loads existing Chronicle entries from disk.
    Must be called once at startup.
    """
    _load_chronicle()


def record_chronicle_entry(event_type, actors, map_id, node_id, summary, data=None, tick=0):
    """Directly create a Chronicle entry without going through the event log.
    
    Use this for events that don't go through the standard event logging system
    but are still significant enough for the Chronicle.
    
    Args:
        event_type: Type of event (e.g., 'faction_event', 'combat_victory').
        actors: List of participant identifiers.
        map_id: Map where event occurred.
        node_id: Node where event occurred.
        summary: Human-readable summary string.
        data: Optional dict of additional data.
        tick: Game tick number.
    
    Returns:
        The created Chronicle entry dict, or None if it's a duplicate.
    """
    entry = {
        'id': _get_next_id(),
        'tick': tick,
        'event_type': event_type,
        'actors': list(actors),
        'map_id': map_id,
        'node_id': node_id,
        'timestamp': time.time(),
        'summary': summary,
        'data': data or {},
    }
    
    with _lock:
        # Check for duplicate (same event_type + same data)
        for existing in _chronicle:
            if (existing.get('event_type') == event_type and 
                existing.get('summary') == summary):
                return None  # Duplicate, don't record
        _chronicle.append(entry)
    
    _append_to_file(entry)
    return entry


def process_new_events(event_log):
    """Process newly created events through the Chronicle consumer.
    
    This is the main entry point for the Chronicle system.
    Call this every tick to consume events from the event log.
    
    Args:
        event_log: List of raw event dicts from the event logger.
    
    Returns:
        Number of new Chronicle entries created this tick.
    """
    return _consume_events(event_log)


def get_chronicle_entries(event_type=None, actor=None, limit=None):
    """Query Chronicle entries.
    
    All filters are optional. When provided, only matching entries are returned.
    
    Args:
        event_type: Filter by event type (e.g., 'quest_accept').
        actor: Filter by participant identifier.
        limit: Maximum number of entries to return (most recent).
    
    Returns:
        List of matching Chronicle entry dicts.
    """
    with _lock:
        entries = list(_chronicle)
    
    if event_type:
        entries = [e for e in entries if e.get('event_type') == event_type]
    if actor:
        entries = [e for e in entries if actor in e.get('actors', [])]
    if limit:
        entries = entries[-limit:]
    
    return entries


def get_recent_chronicle_entries(count=10):
    """Get the most recent Chronicle entries.
    
    Args:
        count: Number of recent entries to return.
    
    Returns:
        List of the most recent Chronicle entry dicts.
    """
    with _lock:
        return list(_chronicle[-count:])


def get_chronicle_count():
    """Return total number of Chronicle entries."""
    with _lock:
        return len(_chronicle)


def clear_chronicle():
    """Clear the Chronicle from memory and disk. Useful for testing."""
    global _last_processed_event_index
    with _lock:
        _chronicle.clear()
        _last_processed_event_index = -1
    _ensure_chronicle_dir()
    with open(CHRONICLE_FILE, 'w', encoding='utf-8') as f:
        f.write('')