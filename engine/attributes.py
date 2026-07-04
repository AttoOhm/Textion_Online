"""
Attributes — Character Foundation (Phase 3B)

Attributes are hidden numeric values representing fundamental character potential.
Range: 0-200
Visibility: Hidden (players do not see raw numbers)

Attributes are used by:
- Players — Core character stats
- Actors — Content definition (NPCs, creatures, etc.)

Attributes increase very slowly through:
- Training
- Discipline progression
- Special quests
- Major life events

This module provides storage, loading, validation, and defaults.
No gameplay usage yet.
"""

# Attribute definitions
VALID_ATTRIBUTES = [
    'willpower',
    'reactiveness',
    'observation',
    'dexterity',
    'constitution',
    'strength',
    'arcana',
    'knowledge',
]

# Attribute ranges
ATTRIBUTE_MIN = 0
ATTRIBUTE_MAX = 200
ATTRIBUTE_DEFAULT = 50

# Human-readable labels for attribute ranges
ATTRIBUTE_LABELS = [
    (0, 20, "Feeble"),
    (21, 40, "Poor"),
    (41, 60, "Average"),
    (61, 80, "Good"),
    (81, 100, "Exceptional"),
    (101, 120, "Master"),
    (121, 140, "Legendary"),
    (141, 160, "Mythic"),
    (161, 180, "Divine"),
    (181, 200, "Transcendent"),
]


def create_default_attributes():
    """Create a default attribute set with all attributes at the default value.
    
    Returns:
        dict: Attribute dictionary with all 8 attributes at default value.
    """
    return {attr: ATTRIBUTE_DEFAULT for attr in VALID_ATTRIBUTES}


def validate_attributes(attributes):
    """Validate an attribute dictionary.
    
    Args:
        attributes: Dictionary of attribute values.
    
    Returns:
        tuple: (is_valid, errors) where errors is a list of error messages.
    """
    errors = []
    
    if not isinstance(attributes, dict):
        return False, ["Attributes must be a dictionary"]
    
    # Check for missing attributes
    for attr in VALID_ATTRIBUTES:
        if attr not in attributes:
            errors.append(f"Missing attribute: {attr}")
    
    # Check for extra attributes
    for attr in attributes:
        if attr not in VALID_ATTRIBUTES:
            errors.append(f"Unknown attribute: {attr}")
    
    # Check for invalid values
    for attr, value in attributes.items():
        if attr in VALID_ATTRIBUTES:
            if not isinstance(value, (int, float)):
                errors.append(f"Attribute '{attr}' must be a number, got {type(value).__name__}")
            elif value < ATTRIBUTE_MIN or value > ATTRIBUTE_MAX:
                errors.append(f"Attribute '{attr}' must be between {ATTRIBUTE_MIN} and {ATTRIBUTE_MAX}, got {value}")
    
    return len(errors) == 0, errors


def clamp_attribute(value):
    """Clamp an attribute value to the valid range.
    
    Args:
        value: The value to clamp.
    
    Returns:
        int: The clamped value.
    """
    return max(ATTRIBUTE_MIN, min(ATTRIBUTE_MAX, int(value)))


def get_attribute_label(value):
    """Get a human-readable label for an attribute value.
    
    Args:
        value: The attribute value.
    
    Returns:
        str: The label for the attribute value.
    """
    for low, high, label in ATTRIBUTE_LABELS:
        if low <= value <= high:
            return label
    return "Unknown"


def get_attribute_value(player_state, attribute_name):
    """Get an attribute value from player state.
    
    Args:
        player_state: The player state dictionary.
        attribute_name: The attribute name.
    
    Returns:
        int: The attribute value, or default if not found.
    """
    attributes = player_state.get('attributes', {})
    return attributes.get(attribute_name, ATTRIBUTE_DEFAULT)


def set_attribute_value(player_state, attribute_name, value):
    """Set an attribute value in player state.
    
    Args:
        player_state: The player state dictionary.
        attribute_name: The attribute name.
        value: The new value.
    
    Returns:
        int: The clamped value that was set.
    """
    if attribute_name not in VALID_ATTRIBUTES:
        raise ValueError(f"Invalid attribute: {attribute_name}")
    
    clamped = clamp_attribute(value)
    player_state.setdefault('attributes', {})[attribute_name] = clamped
    return clamped


def modify_attribute(player_state, attribute_name, amount):
    """Modify an attribute value in player state.
    
    Args:
        player_state: The player state dictionary.
        attribute_name: The attribute name.
        amount: The amount to modify (positive or negative).
    
    Returns:
        int: The new clamped value.
    """
    current = get_attribute_value(player_state, attribute_name)
    return set_attribute_value(player_state, attribute_name, current + amount)


def get_all_attributes(player_state):
    """Get all attribute values from player state.
    
    Args:
        player_state: The player state dictionary.
    
    Returns:
        dict: Dictionary of all attribute values.
    """
    attributes = player_state.get('attributes', {})
    
    # Apply active buffs
    effective_attrs = dict(attributes)
    active_buffs = player_state.get('active_buffs', {})
    
    for buff_stat, buff_data in active_buffs.items():
        if buff_stat in effective_attrs:
            effective_attrs[buff_stat] += buff_data.get('amount', 0)
        else:
            effective_attrs[buff_stat] = buff_data.get('amount', 0)
    
    return {attr: effective_attrs.get(attr, ATTRIBUTE_DEFAULT) for attr in VALID_ATTRIBUTES}


def get_attribute_with_buffs(player_state, attribute_name):
    """Get a single attribute value including active buffs.
    
    Args:
        player_state: Player state dictionary
        attribute_name: Name of the attribute to retrieve
        
    Returns:
        int: Effective attribute value including buffs
    """
    base_value = get_attribute_value(player_state, attribute_name)
    
    # Apply buffs
    active_buffs = player_state.get('active_buffs', {})
    if attribute_name in active_buffs:
        buff_amount = active_buffs[attribute_name].get('amount', 0)
        return base_value + buff_amount
    
    return base_value
