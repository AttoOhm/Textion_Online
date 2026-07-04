"""
Action Resolution Engine (Phase 4B)

Implements the universal action resolution framework defined in:
docs/action_framework_specification.md

This engine provides infrastructure only. No gameplay systems are implemented.

Formula:
    Result = (Attribute + Technique + Modifiers) × BellCurveMultiplier

Key Properties:
- Attribute range: 0-120
- Technique bonus: lvl × 10
- Bell curve multiplier: 0.3-1.7 (step 0.1)
- Outcome levels: Critical Failure, Failure, Partial Success, Success, Exceptional Success
"""

import random
from typing import Optional, Dict, List, Tuple, Any

# ============ CONSTANTS ============

# Attribute range
ATTRIBUTE_MIN = 0
ATTRIBUTE_MAX = 120

# Technique range
TECHNIQUE_LVL_MIN = 1
TECHNIQUE_LVL_MAX = 5
TECHNIQUE_BONUS_PER_LVL = 10

# Bell curve multiplier range
MULTIPLIER_MIN = 0.3
MULTIPLIER_MAX = 1.7
MULTIPLIER_STEP = 0.1

# Outcome thresholds (margin-based)
THRESHOLD_CRITICAL_FAILURE = -20
THRESHOLD_FAILURE = 0
THRESHOLD_PARTIAL_SUCCESS = 20
THRESHOLD_SUCCESS = 40

# Difficulty levels
DIFFICULTY_TRIVIAL = 20
DIFFICULTY_EASY = 40
DIFFICULTY_MODERATE = 60
DIFFICULTY_HARD = 80
DIFFICULTY_EXTREME = 100
DIFFICULTY_LEGENDARY = 120

# ============ ACTION TYPES ============

ACTION_TYPE_OPPOSED = "opposed"
ACTION_TYPE_WORLD = "world"

ACTION_TYPES = [
    ACTION_TYPE_OPPOSED,
    ACTION_TYPE_WORLD
]

# ============ OUTCOME TYPES ============

OUTCOME_CRITICAL_FAILURE = "critical_failure"
OUTCOME_FAILURE = "failure"
OUTCOME_PARTIAL_SUCCESS = "partial_success"
OUTCOME_SUCCESS = "success"
OUTCOME_EXCEPTIONAL_SUCCESS = "exceptional_success"

OUTCOMES = [
    OUTCOME_CRITICAL_FAILURE,
    OUTCOME_FAILURE,
    OUTCOME_PARTIAL_SUCCESS,
    OUTCOME_SUCCESS,
    OUTCOME_EXCEPTIONAL_SUCCESS
]

# ============ BELL CURVE IMPLEMENTATION ============


def generate_bell_curve_multiplier() -> float:
    """Generate a bell curve multiplier using weighted random selection.
    
    Distribution requirements:
    - Approximately 75% of outcomes must fall between 0.8 and 1.2
    - Extreme outcomes must be rare
    - Distribution must be bell-curved
    
    Implementation uses weighted random selection where middle values
    have higher probability than extreme values.
    
    Returns:
        float: Multiplier between 0.3 and 1.7
    """
    # Define possible multiplier values
    multipliers = [round(MULTIPLIER_MIN + i * MULTIPLIER_STEP, 1) 
                   for i in range(int((MULTIPLIER_MAX - MULTIPLIER_MIN) / MULTIPLIER_STEP) + 1)]
    
    # Define weights for bell curve distribution
    # Center values (0.8-1.2) get highest weight
    # Extreme values get lowest weight
    weights = []
    for m in multipliers:
        if 0.8 <= m <= 1.2:
            # Center range: high weight
            weights.append(25)
        elif 0.6 <= m <= 1.4:
            # Middle range: medium weight
            weights.append(10)
        elif 0.4 <= m <= 1.6:
            # Outer range: low weight
            weights.append(3)
        else:
            # Extreme range: very low weight
            weights.append(1)
    
    # Normalize weights to sum to 1.0
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]
    
    # Select multiplier based on weights
    return random.choices(multipliers, weights=weights, k=1)[0]


def validate_multiplier(multiplier: float) -> bool:
    """Validate that a multiplier is within acceptable range.
    
    Args:
        multiplier: The multiplier to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    return MULTIPLIER_MIN <= multiplier <= MULTIPLIER_MAX


# ============ ATTRIBUTE HELPERS ============


def validate_attribute(value: int) -> bool:
    """Validate that an attribute is within acceptable range.
    
    Args:
        value: The attribute value to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    return ATTRIBUTE_MIN <= value <= ATTRIBUTE_MAX


def get_attribute_value(character: Dict, attribute_name: str) -> int:
    """Get an attribute value from a character dictionary.
    
    Args:
        character: Character dictionary with 'attributes' key
        attribute_name: Name of the attribute to retrieve
        
    Returns:
        int: Attribute value (0-120)
    """
    attributes = character.get('attributes', {})
    value = attributes.get(attribute_name, 0)
    
    # Clamp to valid range
    return max(ATTRIBUTE_MIN, min(ATTRIBUTE_MAX, value))


# ============ TECHNIQUE HELPERS ============


def calculate_technique_bonus(lvl: int) -> int:
    """Calculate technique bonus from level.
    
    Args:
        lvl: Technique level (1-5)
        
    Returns:
        int: Bonus value (lvl × 10)
    """
    clamped_lvl = max(TECHNIQUE_LVL_MIN, min(TECHNIQUE_LVL_MAX, lvl))
    return clamped_lvl * TECHNIQUE_BONUS_PER_LVL


def get_technique_bonus(character: Dict, technique_name: str) -> int:
    """Get technique bonus from a character dictionary.
    
    Args:
        character: Character dictionary with 'techniques' key
        technique_name: Name of the technique to retrieve
        
    Returns:
        int: Technique bonus (0-50)
    """
    techniques = character.get('techniques', {})
    
    # Handle both dict and list formats
    if isinstance(techniques, dict):
        technique = techniques.get(technique_name, {})
        lvl = technique.get('lvl', 0) if isinstance(technique, dict) else 0
    elif isinstance(techniques, list):
        # Legacy list format - assume level 1 if present
        lvl = 1 if technique_name in techniques else 0
    else:
        lvl = 0
    
    return calculate_technique_bonus(lvl)


# ============ CONSTRUCTED ATTRIBUTE SYSTEM ============


def calculate_constructed_attribute(character: Dict, attribute_weights: Dict[str, float]) -> float:
    """Calculate a constructed attribute from weighted base attributes.
    
    Formula: Σ(Attribute_i × Weight_i)
    
    Args:
        character: Character dictionary with 'attributes' key
        attribute_weights: Dict of attribute_name -> weight (must sum to 1.0)
        
    Returns:
        float: Constructed attribute value
    """
    total = 0.0
    for attr_name, weight in attribute_weights.items():
        attr_value = get_attribute_value(character, attr_name)
        total += attr_value * weight
    return total


def validate_constructed_attribute(attribute_weights: Dict[str, float]) -> bool:
    """Validate constructed attribute definition.
    
    Rules:
    - At least one attribute required
    - All weights between 0.0 and 1.0
    - Sum of weights ≈ 1.0 (±0.01)
    
    Args:
        attribute_weights: Dict of attribute_name -> weight
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not attribute_weights:
        return False
    
    total = sum(attribute_weights.values())
    if not (0.99 <= total <= 1.01):
        return False
    
    for weight in attribute_weights.values():
        if not (0.0 <= weight <= 1.0):
            return False
    
    return True


def get_damage_modifier(constructed_attribute: float) -> int:
    """Get damage modifier from constructed attribute value.
    
    Formula: floor((Constructed Attribute - 20) / 5)
    
    Scales linearly across full 0-120 range.
    
    Args:
        constructed_attribute: Calculated constructed attribute value
        
    Returns:
        int: Damage modifier (scales with attribute value)
    """
    return int((constructed_attribute - 20) // 5)


def get_attribute_definition(action_def: Dict[str, Any]) -> Dict[str, float]:
    """Get attribute definition from action definition (old or new format).
    
    Supports backward compatibility during migration.
    
    Args:
        action_def: Action definition dictionary
        
    Returns:
        Dict[str, float]: Attribute weights
        
    Raises:
        ValueError: If action definition missing attribute specification
    """
    if "constructed_attribute" in action_def:
        return action_def["constructed_attribute"]
    elif "actor_attribute" in action_def:
        # Legacy format - convert to constructed attribute
        attr = action_def["actor_attribute"]
        return {attr: 1.0}
    else:
        raise ValueError("Action definition missing attribute specification")


# ============ OUTCOME DETERMINATION ============


def determine_outcome(margin: int) -> str:
    """Determine outcome level from margin of success.
    
    Args:
        margin: Margin of success (actor_total - target_total or actor_total - dc)
        
    Returns:
        str: Outcome type
    """
    if margin < THRESHOLD_CRITICAL_FAILURE:
        return OUTCOME_CRITICAL_FAILURE
    elif margin < THRESHOLD_FAILURE:
        return OUTCOME_FAILURE
    elif margin < THRESHOLD_PARTIAL_SUCCESS:
        return OUTCOME_PARTIAL_SUCCESS
    elif margin < THRESHOLD_SUCCESS:
        return OUTCOME_SUCCESS
    else:
        return OUTCOME_EXCEPTIONAL_SUCCESS


def get_outcome_description(outcome: str) -> str:
    """Get human-readable description of an outcome.
    
    Args:
        outcome: Outcome type
        
    Returns:
        str: Description of the outcome
    """
    descriptions = {
        OUTCOME_CRITICAL_FAILURE: "Catastrophic failure",
        OUTCOME_FAILURE: "Action failed",
        OUTCOME_PARTIAL_SUCCESS: "Partial success",
        OUTCOME_SUCCESS: "Success",
        OUTCOME_EXCEPTIONAL_SUCCESS: "Exceptional success"
    }
    return descriptions.get(outcome, "Unknown outcome")


# ============ ACTION RESOLUTION ============


def resolve_self_action(
    actor: Dict,
    attribute_name: str,
    technique_name: Optional[str] = None,
    difficulty: int = DIFFICULTY_MODERATE,
    modifiers: Optional[List[int]] = None,
    action_definition: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Resolve a self action (affects only the actor).
    
    Formula: (Constructed Attribute + Technique + Modifiers) × BellCurveMultiplier
    
    Supports both legacy (attribute_name as string) and new (action_definition with
    constructed_attribute) formats for backward compatibility.
    
    Args:
        actor: Actor character dictionary
        attribute_name: Primary attribute for this action (legacy) or ignored if action_definition provided
        technique_name: Optional technique name
        difficulty: Difficulty class (DC)
        modifiers: List of modifier values
        action_definition: Optional action definition with constructed_attribute
        
    Returns:
        Dict with: total, multiplier, outcome, margin, attribute_value, technique_bonus
    """
    # Get attribute value (support both old and new formats)
    if action_definition:
        # New format: use constructed attribute
        attr_weights = get_attribute_definition(action_definition)
        attribute_value = int(calculate_constructed_attribute(actor, attr_weights))
    else:
        # Legacy format: use single attribute
        attribute_value = get_attribute_value(actor, attribute_name)
    
    technique_bonus = get_technique_bonus(actor, technique_name) if technique_name else 0
    modifier_total = sum(modifiers) if modifiers else 0
    
    # Calculate base total before multiplier
    base_total = attribute_value + technique_bonus + modifier_total
    
    # Apply bell curve multiplier
    multiplier = generate_bell_curve_multiplier()
    total = int(base_total * multiplier)
    
    # Calculate margin against difficulty
    margin = total - difficulty
    
    # Determine outcome
    outcome = determine_outcome(margin)
    
    return {
        'total': total,
        'multiplier': multiplier,
        'outcome': outcome,
        'margin': margin,
        'attribute_value': attribute_value,
        'technique_bonus': technique_bonus,
        'modifier_total': modifier_total,
        'base_total': base_total,
        'difficulty': difficulty,
        'action_type': ACTION_TYPE_SELF
    }


def resolve_opposed_action(
    actor: Dict,
    target: Dict,
    actor_attribute_name: str,
    target_attribute_name: str,
    actor_technique_name: Optional[str] = None,
    target_technique_name: Optional[str] = None,
    modifiers: Optional[List[int]] = None,
    actor_action_definition: Optional[Dict[str, Any]] = None,
    target_action_definition: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Resolve an opposed action (actor vs target).
    
    Formula: (Constructed Attribute + Technique + Modifiers) × BellCurveMultiplier
    
    Supports both legacy (attribute_name as string) and new (action_definition with
    constructed_attribute) formats for backward compatibility.
    
    Args:
        actor: Actor character dictionary
        target: Target character dictionary
        actor_attribute_name: Primary attribute for actor (legacy) or ignored if actor_action_definition provided
        target_attribute_name: Primary attribute for target (legacy) or ignored if target_action_definition provided
        actor_technique_name: Optional technique name for actor
        target_technique_name: Optional technique name for target
        modifiers: List of modifier values for actor
        actor_action_definition: Optional action definition with constructed_attribute for actor
        target_action_definition: Optional action definition with constructed_attribute for target
        
    Returns:
        Dict with: total, multiplier, outcome, margin, actor_total, target_total
    """
    # Get actor attribute value (support both old and new formats)
    if actor_action_definition:
        # New format: use constructed attribute
        actor_attr_weights = get_attribute_definition(actor_action_definition)
        actor_attribute = int(calculate_constructed_attribute(actor, actor_attr_weights))
    else:
        # Legacy format: use single attribute
        actor_attribute = get_attribute_value(actor, actor_attribute_name)
    
    actor_technique = get_technique_bonus(actor, actor_technique_name) if actor_technique_name else 0
    modifier_total = sum(modifiers) if modifiers else 0
    
    # Get target attribute value (support both old and new formats)
    if target_action_definition:
        # New format: use constructed attribute
        target_attr_weights = get_attribute_definition(target_action_definition)
        target_attribute = int(calculate_constructed_attribute(target, target_attr_weights))
    else:
        # Legacy format: use single attribute
        target_attribute = get_attribute_value(target, target_attribute_name)
    
    target_technique = get_technique_bonus(target, target_technique_name) if target_technique_name else 0
    
    # Calculate base totals before multiplier
    actor_base = actor_attribute + actor_technique + modifier_total
    target_base = target_attribute + target_technique
    
    # Apply bell curve multipliers
    actor_multiplier = generate_bell_curve_multiplier()
    target_multiplier = generate_bell_curve_multiplier()
    
    actor_total = int(actor_base * actor_multiplier)
    target_total = int(target_base * target_multiplier)
    
    # Calculate margin (actor - target)
    margin = actor_total - target_total
    
    # Determine outcome
    outcome = determine_outcome(margin)
    
    return {
        'total': actor_total,
        'multiplier': actor_multiplier,
        'outcome': outcome,
        'margin': margin,
        'actor_total': actor_total,
        'target_total': target_total,
        'actor_attribute': actor_attribute,
        'actor_technique': actor_technique,
        'target_attribute': target_attribute,
        'target_technique': target_technique,
        'modifier_total': modifier_total,
        'actor_base': actor_base,
        'target_base': target_base,
        'action_type': ACTION_TYPE_OPPOSED
    }


def resolve_world_action(
    actor: Dict,
    attribute_name: str,
    difficulty: int,
    technique_name: Optional[str] = None,
    modifiers: Optional[List[int]] = None
) -> Dict[str, Any]:
    """Resolve a world action (affects a world element).
    
    Formula: (Attribute + Technique + Modifiers) × BellCurveMultiplier
    
    Args:
        actor: Actor character dictionary
        attribute_name: Primary attribute for this action
        difficulty: Difficulty class (DC)
        technique_name: Optional technique name
        modifiers: List of modifier values
        
    Returns:
        Dict with: total, multiplier, outcome, margin
    """
    # Get base values
    attribute_value = get_attribute_value(actor, attribute_name)
    technique_bonus = get_technique_bonus(actor, technique_name) if technique_name else 0
    modifier_total = sum(modifiers) if modifiers else 0
    
    # Calculate base total before multiplier
    base_total = attribute_value + technique_bonus + modifier_total
    
    # Apply bell curve multiplier
    multiplier = generate_bell_curve_multiplier()
    total = int(base_total * multiplier)
    
    # Calculate margin against difficulty
    margin = total - difficulty
    
    # Determine outcome
    outcome = determine_outcome(margin)
    
    return {
        'total': total,
        'multiplier': multiplier,
        'outcome': outcome,
        'margin': margin,
        'attribute_value': attribute_value,
        'technique_bonus': technique_bonus,
        'modifier_total': modifier_total,
        'base_total': base_total,
        'difficulty': difficulty,
        'action_type': ACTION_TYPE_WORLD
    }


def resolve_social_action(
    actor: Dict,
    target: Dict,
    actor_attribute_name: str,
    target_attribute_name: str,
    actor_technique_name: Optional[str] = None,
    target_technique_name: Optional[str] = None,
    modifiers: Optional[List[int]] = None
) -> Dict[str, Any]:
    """Resolve a social action (influences another character).
    
    Formula: (Attribute + Technique + Modifiers) × BellCurveMultiplier
    
    Args:
        actor: Actor character dictionary
        target: Target character dictionary
        actor_attribute_name: Primary attribute for actor
        target_attribute_name: Primary attribute for target
        actor_technique_name: Optional technique name for actor
        target_technique_name: Optional technique name for target
        modifiers: List of modifier values for actor
        
    Returns:
        Dict with: total, multiplier, outcome, margin
    """
    # Social actions use the same resolution as opposed actions
    return resolve_opposed_action(
        actor=actor,
        target=target,
        actor_attribute_name=actor_attribute_name,
        target_attribute_name=target_attribute_name,
        actor_technique_name=actor_technique_name,
        target_technique_name=target_technique_name,
        modifiers=modifiers
    )


# ============ UNIFIED RESOLUTION ============


def resolve_action(
    action_type: str,
    actor: Dict,
    attribute_name: str,
    target: Optional[Dict] = None,
    target_attribute_name: Optional[str] = None,
    technique_name: Optional[str] = None,
    target_technique_name: Optional[str] = None,
    difficulty: Optional[int] = None,
    modifiers: Optional[List[int]] = None
) -> Dict[str, Any]:
    """Resolve any action using the unified resolution system.
    
    Formula: (Attribute + Technique + Modifiers) × BellCurveMultiplier
    
    Args:
        action_type: Type of action (opposed, world)
        actor: Actor character dictionary
        attribute_name: Primary attribute for actor
        target: Optional target character dictionary
        target_attribute_name: Optional attribute name for target
        technique_name: Optional technique name for actor
        target_technique_name: Optional technique name for target
        difficulty: Optional difficulty class (for world actions)
        modifiers: List of modifier values
        
    Returns:
        Dict with action resolution results
    """
    if action_type == ACTION_TYPE_OPPOSED:
        if target is None or target_attribute_name is None:
            raise ValueError("Opposed actions require a target and target_attribute_name")
        return resolve_opposed_action(
            actor=actor,
            target=target,
            actor_attribute_name=attribute_name,
            target_attribute_name=target_attribute_name,
            actor_technique_name=technique_name,
            target_technique_name=target_technique_name,
            modifiers=modifiers
        )
    elif action_type == ACTION_TYPE_WORLD:
        if difficulty is None:
            raise ValueError("World actions require a difficulty")
        return resolve_world_action(
            actor=actor,
            attribute_name=attribute_name,
            difficulty=difficulty,
            technique_name=technique_name,
            modifiers=modifiers
        )
    else:
        raise ValueError(f"Unknown action type: {action_type}")


# ============ VALIDATION ============


def validate_action_result(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate an action result object.
    
    Args:
        result: Action resolution result
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required fields
    required_fields = ['total', 'multiplier', 'outcome', 'margin']
    for field in required_fields:
        if field not in result:
            errors.append(f"Missing required field: {field}")
    
    # Validate total
    if 'total' in result:
        if not isinstance(result['total'], int):
            errors.append("Total must be an integer")
    
    # Validate multiplier
    if 'multiplier' in result:
        if not validate_multiplier(result['multiplier']):
            errors.append(f"Multiplier {result['multiplier']} out of range [{MULTIPLIER_MIN}, {MULTIPLIER_MAX}]")
    
    # Validate outcome
    if 'outcome' in result:
        if result['outcome'] not in OUTCOMES:
            errors.append(f"Invalid outcome: {result['outcome']}")
    
    # Validate margin
    if 'margin' in result:
        if not isinstance(result['margin'], int):
            errors.append("Margin must be an integer")
    
    return len(errors) == 0, errors


# ============ EXAMPLE ACTIONS ============


def create_example_character(
    name: str,
    attributes: Dict[str, int],
    techniques: Optional[Dict[str, int]] = None
) -> Dict:
    """Create an example character for testing.
    
    Args:
        name: Character name
        attributes: Dictionary of attribute values
        techniques: Optional dictionary of technique levels
        
    Returns:
        Character dictionary
    """
    return {
        'name': name,
        'attributes': attributes,
        'techniques': techniques or {}
    }


def run_example_track_prey():
    """Example: Track Prey action."""
    print("\n=== TRACK PREY ACTION ===")
    
    # Create actor (player)
    player = create_example_character(
        name="Player",
        attributes={
            'observation': 50,
            'dexterity': 40
        },
        techniques={
            'track_prey': 2  # lvl 2
        }
    )
    
    # Create target (wolf)
    wolf = create_example_character(
        name="Wolf",
        attributes={
            'dexterity': 60
        }
    )
    
    # Resolve opposed action
    result = resolve_action(
        action_type=ACTION_TYPE_OPPOSED,
        actor=player,
        attribute_name='observation',
        target=wolf,
        target_attribute_name='dexterity',
        technique_name='track_prey'
    )
    
    print(f"Actor: {player['name']}")
    print(f"Target: {wolf['name']}")
    print(f"Actor Attribute (Observation): {result['actor_attribute']}")
    print(f"Actor Technique Bonus: {result['actor_technique']}")
    print(f"Target Attribute (Dexterity): {result['target_attribute']}")
    print(f"Actor Multiplier: {result['multiplier']}")
    print(f"Actor Total: {result['actor_total']}")
    print(f"Target Total: {result['target_total']}")
    print(f"Margin: {result['margin']}")
    print(f"Outcome: {result['outcome']}")
    
    return result


def run_example_hide():
    """Example: Hide action."""
    print("\n=== HIDE ACTION ===")
    
    # Create actor (player)
    player = create_example_character(
        name="Player",
        attributes={
            'dexterity': 45,
            'observation': 35
        },
        techniques={
            'stealth': 1  # lvl 1
        }
    )
    
    # Resolve world action (hide in bushes)
    result = resolve_action(
        action_type=ACTION_TYPE_WORLD,
        actor=player,
        attribute_name='dexterity',
        difficulty=DIFFICULTY_EASY,
        technique_name='stealth'
    )
    
    print(f"Actor: {player['name']}")
    print(f"Attribute (Dexterity): {result['attribute_value']}")
    print(f"Technique Bonus: {result['technique_bonus']}")
    print(f"Multiplier: {result['multiplier']}")
    print(f"Total: {result['total']}")
    print(f"Difficulty: {result['difficulty']}")
    print(f"Margin: {result['margin']}")
    print(f"Outcome: {result['outcome']}")
    
    return result


def run_example_hide_opposed():
    """Example: Hide action (opposed - hider vs observers)."""
    print("\n=== HIDE ACTION (OPPOSED) ===")
    
    # Create hider (player)
    hider = create_example_character(
        name="Player",
        attributes={
            'dexterity': 45,
            'observation': 35
        },
        techniques={
            'stealth': 1  # lvl 1
        }
    )
    
    # Create observer 1 (guard)
    observer1 = create_example_character(
        name="Guard",
        attributes={
            'observation': 40
        }
    )
    
    # Create observer 2 (wolf)
    observer2 = create_example_character(
        name="Wolf",
        attributes={
            'observation': 60
        }
    )
    
    # Resolve against observer 1
    result1 = resolve_action(
        action_type=ACTION_TYPE_OPPOSED,
        actor=hider,
        attribute_name='dexterity',
        target=observer1,
        target_attribute_name='observation',
        technique_name='stealth'
    )
    
    # Resolve against observer 2
    result2 = resolve_action(
        action_type=ACTION_TYPE_OPPOSED,
        actor=hider,
        attribute_name='dexterity',
        target=observer2,
        target_attribute_name='observation',
        technique_name='stealth'
    )
    
    print(f"Hider: {hider['name']}")
    print(f"Hider Attribute (Dexterity): {result1['actor_attribute']}")
    print(f"Hider Technique Bonus: {result1['actor_technique']}")
    print(f"Hider Total: {result1['actor_total']}")
    print(f"\nObserver 1: {observer1['name']}")
    print(f"Observer 1 Attribute (Observation): {result1['target_attribute']}")
    print(f"Observer 1 Total: {result1['target_total']}")
    print(f"Margin vs Observer 1: {result1['margin']}")
    print(f"Outcome vs Observer 1: {result1['outcome']}")
    print(f"\nObserver 2: {observer2['name']}")
    print(f"Observer 2 Attribute (Observation): {result2['target_attribute']}")
    print(f"Observer 2 Total: {result2['target_total']}")
    print(f"Margin vs Observer 2: {result2['margin']}")
    print(f"Outcome vs Observer 2: {result2['outcome']}")
    
    return result1, result2


def run_example_repair():
    """Example: Repair Item action."""
    print("\n=== REPAIR ITEM ACTION ===")
    
    # Create actor (player)
    player = create_example_character(
        name="Player",
        attributes={
            'dexterity': 40,
            'knowledge': 35
        },
        techniques={
            'smithing': 1  # lvl 1
        }
    )
    
    # Resolve world action (repair sword)
    result = resolve_action(
        action_type=ACTION_TYPE_WORLD,
        actor=player,
        attribute_name='dexterity',
        difficulty=DIFFICULTY_MODERATE,
        technique_name='smithing'
    )
    
    print(f"Actor: {player['name']}")
    print(f"Attribute (Dexterity): {result['attribute_value']}")
    print(f"Technique Bonus: {result['technique_bonus']}")
    print(f"Multiplier: {result['multiplier']}")
    print(f"Total: {result['total']}")
    print(f"Difficulty: {result['difficulty']}")
    print(f"Margin: {result['margin']}")
    print(f"Outcome: {result['outcome']}")
    
    return result


def run_all_examples():
    """Run all example actions."""
    print("=" * 60)
    print("ACTION RESOLUTION ENGINE - EXAMPLE ACTIONS")
    print("=" * 60)
    
    results = []
    results.append(run_example_track_prey())
    results.append(run_example_hide())
    results.append(run_example_hide_opposed())
    results.append(run_example_repair())
    
    print("\n" + "=" * 60)
    print("ALL EXAMPLES COMPLETE")
    print("=" * 60)
    
    return results


# ============ MAIN ============

if __name__ == "__main__":
    run_all_examples()