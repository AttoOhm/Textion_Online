"""
Disciplines — Character Foundation (Phase 3B)

Disciplines are knowledge fields representing what a character has learned.
Range: 0-200
Visibility: Hidden

Disciplines are NOT XP systems.
Disciplines are NOT classes.
Disciplines increase very slowly.

This module provides storage, loading, validation, and defaults.
No gameplay usage yet.
No XP tables. No level systems. No progression formulas.
"""

# Discipline definitions
VALID_DISCIPLINES = [
    'tracking',
    'swordsmanship',
    'smithing',
    'necromancy',
    'animal_handling',
    'sun_faith',
    'stealth',
    'alchemy',
]

# Discipline ranges
DISCIPLINE_MIN = 0
DISCIPLINE_MAX = 200
DISCIPLINE_DEFAULT = 0

# Human-readable labels for discipline ranges
DISCIPLINE_LABELS = [
    (0, 20, "Novice"),
    (21, 40, "Apprentice"),
    (41, 60, "Journeyman"),
    (61, 80, "Expert"),
    (81, 100, "Master"),
    (101, 120, "Grandmaster"),
    (121, 140, "Legendary"),
    (141, 160, "Mythic"),
    (161, 180, "Divine"),
    (181, 200, "Transcendent"),
]


def create_default_disciplines():
    """Create a default discipline set with all disciplines at the default value.
    
    Returns:
        dict: Discipline dictionary with all disciplines at default value.
    """
    return {disc: DISCIPLINE_DEFAULT for disc in VALID_DISCIPLINES}


def validate_disciplines(disciplines):
    """Validate a discipline dictionary.
    
    Args:
        disciplines: Dictionary of discipline values.
    
    Returns:
        tuple: (is_valid, errors) where errors is a list of error messages.
    """
    errors = []
    
    if not isinstance(disciplines, dict):
        return False, ["Disciplines must be a dictionary"]
    
    # Check for extra disciplines
    for disc in disciplines:
        if disc not in VALID_DISCIPLINES:
            errors.append(f"Unknown discipline: {disc}")
    
    # Check for invalid values
    for disc, value in disciplines.items():
        if disc in VALID_DISCIPLINES:
            if not isinstance(value, (int, float)):
                errors.append(f"Discipline '{disc}' must be a number, got {type(value).__name__}")
            elif value < DISCIPLINE_MIN or value > DISCIPLINE_MAX:
                errors.append(f"Discipline '{disc}' must be between {DISCIPLINE_MIN} and {DISCIPLINE_MAX}, got {value}")
    
    return len(errors) == 0, errors


def clamp_discipline(value):
    """Clamp a discipline value to the valid range.
    
    Args:
        value: The value to clamp.
    
    Returns:
        int: The clamped value.
    """
    return max(DISCIPLINE_MIN, min(DISCIPLINE_MAX, int(value)))


def get_discipline_label(value):
    """Get a human-readable label for a discipline value.
    
    Args:
        value: The discipline value.
    
    Returns:
        str: The label for the discipline value.
    """
    for low, high, label in DISCIPLINE_LABELS:
        if low <= value <= high:
            return label
    return "Unknown"


def get_discipline_value(player_state, discipline_name):
    """Get a discipline value from player state.
    
    Args:
        player_state: The player state dictionary.
        discipline_name: The discipline name.
    
    Returns:
        int: The discipline value, or default if not found.
    """
    disciplines = player_state.get('disciplines', {})
    return disciplines.get(discipline_name, DISCIPLINE_DEFAULT)


def set_discipline_value(player_state, discipline_name, value):
    """Set a discipline value in player state.
    
    Args:
        player_state: The player state dictionary.
        discipline_name: The discipline name.
        value: The new value.
    
    Returns:
        int: The clamped value that was set.
    """
    clamped = clamp_discipline(value)
    player_state.setdefault('disciplines', {})[discipline_name] = clamped
    return clamped


def modify_discipline(player_state, discipline_name, amount):
    """Modify a discipline value in player state.
    
    Args:
        player_state: The player state dictionary.
        discipline_name: The discipline name.
        amount: The amount to modify (positive or negative).
    
    Returns:
        int: The new clamped value.
    """
    current = get_discipline_value(player_state, discipline_name)
    return set_discipline_value(player_state, discipline_name, current + amount)


def get_all_disciplines(player_state):
    """Get all discipline values from player state.
    
    Args:
        player_state: The player state dictionary.
    
    Returns:
        dict: Dictionary of all discipline values.
    """
    disciplines = player_state.get('disciplines', {})
    return {disc: disciplines.get(disc, DISCIPLINE_DEFAULT) for disc in VALID_DISCIPLINES}