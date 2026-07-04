"""
Techniques — Character Foundation (Phase 3B)

Techniques are specific learned abilities representing concrete actions.
Levels: 1-5
Belong to disciplines.

This module provides storage, loading, validation, and defaults.
No gameplay usage yet.
No execution logic. No effects. No combat integration.
No learning system. No forgetting system.
"""

# Technique level range
TECHNIQUE_LEVEL_MIN = 1
TECHNIQUE_LEVEL_MAX = 5
TECHNIQUE_LEVEL_DEFAULT = 1

# Technique capacity (frozen)
TECHNIQUE_CAPACITY = {
    'minor': 8,
    'major': 6,
    'master': 4,
    'legendary': 2,
}

# Valid technique tiers
VALID_TIERS = ['minor', 'major', 'master', 'legendary']


def create_technique(technique_id, level=1, discipline=None):
    """Create a technique dictionary.
    
    Args:
        technique_id: The technique identifier.
        level: The technique level (1-5).
        discipline: The discipline this technique belongs to.
    
    Returns:
        dict: The technique dictionary.
    """
    return {
        'id': technique_id,
        'level': clamp_technique_level(level),
        'discipline': discipline,
    }


def validate_technique(technique):
    """Validate a technique dictionary.
    
    Args:
        technique: The technique dictionary to validate.
    
    Returns:
        tuple: (is_valid, errors) where errors is a list of error messages.
    """
    errors = []
    
    if not isinstance(technique, dict):
        return False, ["Technique must be a dictionary"]
    
    if 'id' not in technique:
        errors.append("Technique missing 'id'")
    
    if 'level' in technique:
        level = technique['level']
        if not isinstance(level, (int, float)):
            errors.append(f"Technique level must be a number, got {type(level).__name__}")
        elif level < TECHNIQUE_LEVEL_MIN or level > TECHNIQUE_LEVEL_MAX:
            errors.append(f"Technique level must be between {TECHNIQUE_LEVEL_MIN} and {TECHNIQUE_LEVEL_MAX}, got {level}")
    
    return len(errors) == 0, errors


def validate_techniques(techniques):
    """Validate a techniques dictionary.
    
    Args:
        techniques: Dictionary of technique_id -> technique data.
    
    Returns:
        tuple: (is_valid, errors) where errors is a list of error messages.
    """
    errors = []
    
    if not isinstance(techniques, dict):
        return False, ["Techniques must be a dictionary"]
    
    for tech_id, tech_data in techniques.items():
        if not isinstance(tech_data, dict):
            errors.append(f"Technique '{tech_id}' must be a dictionary")
            continue
        
        is_valid, tech_errors = validate_technique(tech_data)
        if not is_valid:
            errors.extend([f"Technique '{tech_id}': {e}" for e in tech_errors])
    
    return len(errors) == 0, errors


def clamp_technique_level(level):
    """Clamp a technique level to the valid range.
    
    Args:
        level: The level to clamp.
    
    Returns:
        int: The clamped level.
    """
    return max(TECHNIQUE_LEVEL_MIN, min(TECHNIQUE_LEVEL_MAX, int(level)))


def get_technique_level(technique):
    """Get the level of a technique.
    
    Args:
        technique: The technique dictionary.
    
    Returns:
        int: The technique level.
    """
    return technique.get('level', TECHNIQUE_LEVEL_DEFAULT)


def get_technique_discipline(technique):
    """Get the discipline of a technique.
    
    Args:
        technique: The technique dictionary.
    
    Returns:
        str or None: The discipline name, or None if not set.
    """
    return technique.get('discipline')


def get_techniques_by_discipline(player_state, discipline_name):
    """Get all techniques belonging to a specific discipline.
    
    Args:
        player_state: The player state dictionary.
        discipline_name: The discipline name.
    
    Returns:
        dict: Dictionary of technique_id -> technique data for the discipline.
    """
    techniques = player_state.get('techniques', {})
    return {
        tech_id: tech_data
        for tech_id, tech_data in techniques.items()
        if tech_data.get('discipline') == discipline_name
    }


def get_technique_count(player_state):
    """Get the total number of techniques the player has.
    
    Args:
        player_state: The player state dictionary.
    
    Returns:
        int: The number of techniques.
    """
    return len(player_state.get('techniques', {}))


def get_technique_count_by_tier(player_state, tier):
    """Get the number of techniques the player has in a specific tier.
    
    Args:
        player_state: The player state dictionary.
        tier: The tier to count (minor, major, master, legendary).
    
    Returns:
        int: The number of techniques in the tier.
    """
    if tier not in VALID_TIERS:
        raise ValueError(f"Invalid tier: {tier}")
    
    techniques = player_state.get('techniques', {})
    count = 0
    for tech_id, tech_data in techniques.items():
        level = tech_data.get('level', TECHNIQUE_LEVEL_DEFAULT)
        if tier == 'minor' and level == 1:
            count += 1
        elif tier == 'major' and level == 2:
            count += 1
        elif tier == 'master' and level == 3:
            count += 1
        elif tier == 'legendary' and level == 4:
            count += 1
    return count


def validate_technique_capacity(player_state):
    """Validate that the player's technique count is within capacity limits.
    
    Args:
        player_state: The player state dictionary.
    
    Returns:
        tuple: (is_valid, errors) where errors is a list of error messages.
    """
    errors = []
    
    for tier, max_slots in TECHNIQUE_CAPACITY.items():
        count = get_technique_count_by_tier(player_state, tier)
        if count > max_slots:
            errors.append(f"Too many {tier} techniques: {count}/{max_slots}")
    
    return len(errors) == 0, errors


def add_technique(player_state, technique_id, level=1, discipline=None):
    """Add a technique to the player's technique list.
    
    Args:
        player_state: The player state dictionary.
        technique_id: The technique identifier.
        level: The technique level (1-5).
        discipline: The discipline this technique belongs to.
    
    Returns:
        dict: The added technique dictionary, or None if capacity exceeded.
    """
    techniques = player_state.setdefault('techniques', {})
    
    if technique_id in techniques:
        return techniques[technique_id]
    
    # Check capacity
    is_valid, errors = validate_technique_capacity(player_state)
    if not is_valid:
        return None
    
    technique = create_technique(technique_id, level, discipline)
    techniques[technique_id] = technique
    return technique


def remove_technique(player_state, technique_id):
    """Remove a technique from the player's technique list.
    
    Args:
        player_state: The player state dictionary.
        technique_id: The technique identifier.
    
    Returns:
        bool: True if the technique was removed, False if not found.
    """
    techniques = player_state.get('techniques', {})
    if technique_id in techniques:
        del techniques[technique_id]
        return True
    return False


def get_technique(player_state, technique_id):
    """Get a technique from the player's technique list.
    
    Args:
        player_state: The player state dictionary.
        technique_id: The technique identifier.
    
    Returns:
        dict or None: The technique dictionary, or None if not found.
    """
    return player_state.get('techniques', {}).get(technique_id)


def get_all_techniques(player_state):
    """Get all techniques from the player's technique list.
    
    Args:
        player_state: The player state dictionary.
    
    Returns:
        dict: Dictionary of technique_id -> technique data.
    """
    return dict(player_state.get('techniques', {}))