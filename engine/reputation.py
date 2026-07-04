"""
Reputation System — Phase 2D

Reputation is simulation state: a persistent numerical record of how
actors and factions view the player. It is NOT NPC memory, rumors,
AI personality, dialogue generation, or emotion simulation.

Scale: 0–1000
  0-99       Very Bad
  100-399    Bad
  400-599    Neutral
  600-899    Good
  900-1000   Very Good

Default: 500 (Neutral)

Two types:
  - Actor reputation: per-actor numerical value
  - Faction reputation: per-faction numerical value

Stored on the player state, not on actors.
"""

from engine.event_logger import create_event


# Reputation scale constants
REPUTATION_MIN = 0
REPUTATION_MAX = 1000
REPUTATION_DEFAULT = 500

# Reputation ranges for display
REPUTATION_RANGES = [
    (0, 99, "Very Bad"),
    (100, 399, "Bad"),
    (400, 599, "Neutral"),
    (600, 899, "Good"),
    (900, 1000, "Very Good"),
]


def _clamp(value):
    """Clamp a value to the valid reputation range."""
    return max(REPUTATION_MIN, min(REPUTATION_MAX, value))


def _get_reputation_dict(player_state, key):
    """Get the reputation dict for a key ('actors' or 'factions')."""
    return player_state.setdefault('reputation', {}).setdefault(key, {})


def get_actor_reputation(player_state, actor_id):
    """Get the player's reputation with a specific actor.
    
    Returns the reputation value (0-1000), defaulting to 500 if not set.
    """
    actors = _get_reputation_dict(player_state, 'actors')
    return actors.get(actor_id, REPUTATION_DEFAULT)


def modify_actor_reputation(player_state, actor_id, amount, reason=None):
    """Modify the player's reputation with a specific actor.
    
    Args:
        player_state: The player state dict.
        actor_id: The actor to modify reputation with.
        amount: The change amount (positive = increase, negative = decrease).
        reason: Optional reason string for the event log.
    
    Returns:
        The new reputation value after clamping.
    """
    actors = _get_reputation_dict(player_state, 'actors')
    old_value = actors.get(actor_id, REPUTATION_DEFAULT)
    new_value = _clamp(old_value + amount)
    actors[actor_id] = new_value
    
    # Generate reputation event
    pos = player_state.get('position', {'map_id': 'village', 'node_id': 'village_center'})
    create_event(
        'reputation',
        pos['map_id'],
        pos['node_id'],
        ['default_player', actor_id],
        data={
            'target': actor_id,
            'change': amount,
            'new_value': new_value,
            'old_value': old_value,
            'reason': reason,
        }
    )
    
    return new_value


def get_faction_reputation(player_state, faction_id):
    """Get the player's reputation with a specific faction.
    
    Returns the reputation value (0-1000), defaulting to 500 if not set.
    """
    factions = _get_reputation_dict(player_state, 'factions')
    return factions.get(faction_id, REPUTATION_DEFAULT)


def modify_faction_reputation(player_state, faction_id, amount, reason=None):
    """Modify the player's reputation with a specific faction.
    
    Args:
        player_state: The player state dict.
        faction_id: The faction to modify reputation with.
        amount: The change amount (positive = increase, negative = decrease).
        reason: Optional reason string for the event log.
    
    Returns:
        The new reputation value after clamping.
    """
    factions = _get_reputation_dict(player_state, 'factions')
    old_value = factions.get(faction_id, REPUTATION_DEFAULT)
    new_value = _clamp(old_value + amount)
    factions[faction_id] = new_value
    
    # Generate reputation event
    pos = player_state.get('position', {'map_id': 'village', 'node_id': 'village_center'})
    create_event(
        'reputation',
        pos['map_id'],
        pos['node_id'],
        ['default_player'],
        data={
            'target': faction_id,
            'change': amount,
            'new_value': new_value,
            'old_value': old_value,
            'reason': reason,
        }
    )
    
    return new_value


def get_reputation_label(value):
    """Get a human-readable label for a reputation value."""
    for low, high, label in REPUTATION_RANGES:
        if low <= value <= high:
            return label
    return "Unknown"


def apply_quest_reputation_rewards(player_state, quest_data):
    """Apply reputation rewards from a completed quest.
    
    Quest data may contain:
    {
        "reputation": {
            "actor": {"aldric": 50},
            "faction": {"village_guard": 25}
        }
    }
    
    Args:
        player_state: The player state dict.
        quest_data: The quest definition dict.
    
    Returns:
        A dict of applied changes: {"actors": {...}, "factions": {...}}
    """
    rep_rewards = quest_data.get('reputation', {})
    applied = {'actors': {}, 'factions': {}}
    
    # Actor reputation rewards
    actor_rewards = rep_rewards.get('actor', {})
    for actor_id, amount in actor_rewards.items():
        new_value = modify_actor_reputation(player_state, actor_id, amount, reason=f"quest_reward")
        applied['actors'][actor_id] = new_value
    
    # Faction reputation rewards
    faction_rewards = rep_rewards.get('faction', {})
    for faction_id, amount in faction_rewards.items():
        new_value = modify_faction_reputation(player_state, faction_id, amount, reason=f"quest_reward")
        applied['factions'][faction_id] = new_value
    
    return applied


def get_all_reputations(player_state):
    """Get a summary of all reputation values.
    
    Returns:
        {
            "actors": {"aldric": 650, "grim": 550},
            "factions": {"village_guard": 700}
        }
    """
    rep = player_state.get('reputation', {})
    return {
        'actors': dict(rep.get('actors', {})),
        'factions': dict(rep.get('factions', {})),
    }