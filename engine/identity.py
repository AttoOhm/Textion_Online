"""
Identity — Character Foundation (Phase 3B)

Identity is emergent — it arises from a character's accumulated choices and experiences.

Key Properties:
- Identity is NOT selected
- Identity is NOT a class
- Identity is NOT stored as a primary field
- Identity is social recognition

Identity is computed on-demand from character state.
This module provides a stub API for future implementation.
No identity logic is implemented yet.
"""

# Identity sources and their weights
IDENTITY_SOURCES = {
    'disciplines': 'high',
    'techniques': 'medium',
    'reputation': 'medium',
    'affiliations': 'low',
    'achievements': 'low',
    'actions': 'low',
}


def compute_identity(player_state):
    """Compute identity labels from character state.
    
    This is a stub function. It returns an empty list.
    Identity computation will be implemented in a future phase.
    
    Args:
        player_state: The player state dictionary.
    
    Returns:
        list: Empty list (identity not yet implemented).
    """
    # TODO: Implement identity computation in future phase
    return []


def get_identity_labels(player_state):
    """Get identity labels for a player.
    
    This is a stub function. It returns an empty list.
    Identity computation will be implemented in a future phase.
    
    Args:
        player_state: The player state dictionary.
    
    Returns:
        list: Empty list (identity not yet implemented).
    """
    return compute_identity(player_state)


def get_identity_description(player_state):
    """Get a human-readable description of a player's identity.
    
    This is a stub function. It returns a default description.
    Identity computation will be implemented in a future phase.
    
    Args:
        player_state: The player state dictionary.
    
    Returns:
        str: Default description (identity not yet implemented).
    """
    labels = compute_identity(player_state)
    if labels:
        return ", ".join(labels)
    return "Unknown"