"""
Combat Engine (Phase 6D)

Implements the first vertical slice of combat.

Uses existing systems:
- Long Actions
- Action Resolution
- Effects
- Inventory
- Equipment
- Engagement Graph
- Combat Foundation Freeze

Implements only:
- attack <target>

No techniques. No magic. No special attacks. No combat AI.
"""

import random
import time
from typing import Optional, Dict, List, Any

# ============ CONSTANTS ============

# Combat events
EVENT_ATTACK_STARTED = "attack_started"
EVENT_ATTACK_HIT = "attack_hit"
EVENT_ATTACK_MISSED = "attack_missed"
EVENT_ACTOR_DOWNED = "actor_downed"
EVENT_ACTOR_DIED = "actor_died"
EVENT_GROUP_JOINED = "group_joined"
EVENT_GROUP_LEFT = "group_left"
EVENT_GROUP_MERGED = "group_merged"
EVENT_GROUP_SPLIT = "group_split"

# HP states
HP_STATE_UNHARMED = "unharmed"
HP_STATE_SCRATCHED = "scratched"
HP_STATE_WOUNDED = "wounded"
HP_STATE_SEVERELY_WOUNDED = "severely_wounded"
HP_STATE_NEAR_DEATH = "near_death"
HP_STATE_DOWNED = "downed"
HP_STATE_DEAD = "dead"

# Damage types
DAMAGE_SLASHING = "slashing"
DAMAGE_PIERCING = "piercing"
DAMAGE_BLUDGEONING = "bludgeoning"
DAMAGE_HEAT = "heat"
DAMAGE_COLD = "cold"
DAMAGE_ARCANA_OVER = "overpressured_arcana"
DAMAGE_ARCANA_UNDER = "underpressured_arcana"
DAMAGE_HOLY_LIFE = "holy_life"
DAMAGE_HOLY_DEATH = "holy_death"

# Default HP values
DEFAULT_HP = 100
DEATH_THRESHOLD = -50

# ============ ATTACK PROFILES ============


# Targeting modes
TARGETING_MELEE = "melee"
TARGETING_RANGED = "ranged"
TARGETING_HYBRID = "hybrid"

# Target scopes
TARGET_SCOPE_SELF = "self"
TARGET_SCOPE_SINGLE_ACTOR = "single_actor"
TARGET_SCOPE_COMBAT_GROUP = "combat_group"
TARGET_SCOPE_PARTY = "party"
TARGET_SCOPE_NODE = "node"

ATTACK_PROFILES = {
    "unarmed": {
        "id": "unarmed",
        "name": "Unarmed Attack",
        "damage_type": DAMAGE_BLUDGEONING,
        "base_damage": 3,
        "constructed_attribute": {
            "strength": 1.0
        },
        "apply_attribute_damage_bonus": True,
        "is_melee": True,
        "is_ranged": False,
        "targeting_mode": TARGETING_MELEE,
        "target_scope": TARGET_SCOPE_SINGLE_ACTOR,
    },
    "sword": {
        "id": "sword",
        "name": "Sword Attack",
        "damage_type": DAMAGE_SLASHING,
        "base_damage": 6,
        "constructed_attribute": {
            "strength": 0.6,
            "dexterity": 0.4
        },
        "apply_attribute_damage_bonus": True,
        "is_melee": True,
        "is_ranged": False,
        "targeting_mode": TARGETING_MELEE,
        "target_scope": TARGET_SCOPE_SINGLE_ACTOR,
    },
    "dagger": {
        "id": "dagger",
        "name": "Dagger Attack",
        "damage_type": DAMAGE_PIERCING,
        "base_damage": 5,
        "constructed_attribute": {
            "dexterity": 0.7,
            "observation": 0.3
        },
        "apply_attribute_damage_bonus": True,
        "is_melee": True,
        "is_ranged": False,
        "targeting_mode": TARGETING_MELEE,
        "target_scope": TARGET_SCOPE_SINGLE_ACTOR,
    },
    "warhammer": {
        "id": "warhammer",
        "name": "Hammer Attack",
        "damage_type": DAMAGE_BLUDGEONING,
        "base_damage": 7,
        "constructed_attribute": {
            "strength": 1.0
        },
        "apply_attribute_damage_bonus": True,
        "is_melee": True,
        "is_ranged": False,
        "targeting_mode": TARGETING_MELEE,
        "target_scope": TARGET_SCOPE_SINGLE_ACTOR,
    },
    "bite": {
        "id": "bite",
        "name": "Bite",
        "damage_type": DAMAGE_PIERCING,
        "base_damage": 12,
        "constructed_attribute": {
            "strength": 1.0
        },
        "apply_attribute_damage_bonus": True,
        "is_melee": True,
        "is_ranged": False,
        "targeting_mode": TARGETING_MELEE,
        "target_scope": TARGET_SCOPE_SINGLE_ACTOR,
    },
    "claw": {
        "id": "claw",
        "name": "Claw",
        "damage_type": DAMAGE_SLASHING,
        "base_damage": 10,
        "constructed_attribute": {
            "strength": 0.7,
            "reactiveness": 0.3
        },
        "apply_attribute_damage_bonus": True,
        "is_melee": True,
        "is_ranged": False,
        "targeting_mode": TARGETING_MELEE,
        "target_scope": TARGET_SCOPE_SINGLE_ACTOR,
    },
    "bow": {
        "id": "bow",
        "name": "Bow Attack",
        "damage_type": DAMAGE_PIERCING,
        "base_damage": 5,
        "constructed_attribute": {
            "dexterity": 0.5,
            "observation": 0.3,
            "reactiveness": 0.2
        },
        "apply_attribute_damage_bonus": True,
        "is_melee": False,
        "is_ranged": True,
        "targeting_mode": TARGETING_RANGED,
        "target_scope": TARGET_SCOPE_SINGLE_ACTOR,
    },
}


def get_attack_profile(profile_id: str) -> Dict[str, Any]:
    """Get an attack profile by ID."""
    return ATTACK_PROFILES.get(profile_id, ATTACK_PROFILES["unarmed"])


def get_weapon_attack_profile(equipment_engine, actor_id: str) -> Dict[str, Any]:
    """Get attack profile based on equipped weapon."""
    from engine.items import get_item_definition

    equipped = equipment_engine.get_equipped_item(actor_id, "main_hand")
    if not equipped:
        return ATTACK_PROFILES["unarmed"]

    item_id = equipped.get("item_id", "")
    item_def = get_item_definition(item_id)
    if not item_def:
        return ATTACK_PROFILES["unarmed"]

    subtype = item_def.get("subtype", "sword")

    profile_map = {
        "sword": "sword",
        "axe": "sword",
        "hatchet": "sword",
        "dagger": "dagger",
        "bow": "bow",
        "warhammer": "warhammer",
        "mace": "warhammer",
        "pickaxe": "warhammer",
    }

    profile_id = profile_map.get(subtype, "unarmed")
    return ATTACK_PROFILES.get(profile_id, ATTACK_PROFILES["unarmed"])


# ============ HP SYSTEM ============


def get_hp_state(current_hp: int, max_hp: int) -> str:
    """Get the HP state based on current and max HP."""
    if current_hp <= DEATH_THRESHOLD:
        return HP_STATE_DEAD
    if current_hp <= 0:
        return HP_STATE_DOWNED
    if current_hp <= max_hp * 0.1:
        return HP_STATE_NEAR_DEATH
    if current_hp <= max_hp * 0.3:
        return HP_STATE_SEVERELY_WOUNDED
    if current_hp <= max_hp * 0.5:
        return HP_STATE_WOUNDED
    if current_hp <= max_hp * 0.8:
        return HP_STATE_SCRATCHED
    return HP_STATE_UNHARMED


def apply_damage(current_hp: int, damage: int) -> int:
    """Apply damage to HP."""
    return current_hp - damage


def is_downed(current_hp: int) -> bool:
    """Check if actor is downed."""
    return current_hp <= 0


def is_dead(current_hp: int) -> bool:
    """Check if actor is dead."""
    return current_hp <= DEATH_THRESHOLD


# ============ DAMAGE PIPELINE ============


def calculate_damage(
    base_damage: int,
    damage_type: str,
    shield_absorption: int = 0,
    armor_reduction: float = 0.0,
) -> Dict[str, Any]:
    """Calculate damage through the pipeline.

    Pipeline:
    Incoming Damage
    ↓
    Shield Absorption
    ↓
    Armor Reduction
    ↓
    HP Damage
    """
    after_shield = max(0, base_damage - shield_absorption)
    after_armor = int(after_shield * (1.0 - armor_reduction))
    hp_damage = max(0, after_armor)

    return {
        "base_damage": base_damage,
        "damage_type": damage_type,
        "shield_absorption": shield_absorption,
        "armor_reduction": armor_reduction,
        "after_shield": after_shield,
        "after_armor": after_armor,
        "hp_damage": hp_damage,
    }


# ============ WEAPON SYSTEM ============


def get_weapon_damage(equipment_engine, actor_id: str) -> Dict[str, Any]:
    """Get damage from equipped weapon."""
    from engine.items import get_item_definition

    equipped = equipment_engine.get_equipped_item(actor_id, "main_hand")
    if not equipped:
        return {
            "weapon": "unarmed",
            "damage_min": 5,
            "damage_max": 10,
            "damage_type": DAMAGE_BLUDGEONING,
        }

    item_id = equipped.get("item_id", "")
    item_def = get_item_definition(item_id)
    if not item_def:
        return {
            "weapon": "unarmed",
            "damage_min": 5,
            "damage_max": 10,
            "damage_type": DAMAGE_BLUDGEONING,
        }

    damage = item_def.get("damage", 10)
    subtype = item_def.get("subtype", "sword")

    damage_type_map = {
        "sword": DAMAGE_SLASHING,
        "axe": DAMAGE_SLASHING,
        "dagger": DAMAGE_PIERCING,
        "bow": DAMAGE_PIERCING,
        "warhammer": DAMAGE_BLUDGEONING,
        "mace": DAMAGE_BLUDGEONING,
        "shield": DAMAGE_BLUDGEONING,
    }
    damage_type = damage_type_map.get(subtype, DAMAGE_SLASHING)

    return {
        "weapon": item_id,
        "damage_min": max(1, damage - 5),
        "damage_max": damage + 5,
        "damage_type": damage_type,
    }


def get_arrow_damage(equipment_engine, actor_id: str) -> int:
    """Get arrow damage for bow attacks.
    
    Checks for equipped quiver in off_hand, then reads arrow type from quiver.
    
    Args:
        equipment_engine: Equipment engine instance
        actor_id: Actor using the bow
        
    Returns:
        int: Arrow damage (0 if no quiver/arrow equipped)
    """
    from engine.items import get_item_definition
    
    # Check off_hand for quiver (container system)
    quiver = equipment_engine.get_equipped_item(actor_id, "off_hand")
    if not quiver:
        return 0
    
    # Verify it's a quiver
    quiver_id = quiver.get("item_id", "")
    quiver_def = get_item_definition(quiver_id)
    if not quiver_def or quiver_def.get("subtype") != "quiver":
        return 0
    
    # Get arrow type from quiver
    arrow_item_id = quiver.get("arrow_item_id")
    if not arrow_item_id:
        return 0
    
    # Get arrow damage
    arrow_def = get_item_definition(arrow_item_id)
    if not arrow_def:
        return 0
    
    return arrow_def.get("damage", 0)


def consume_arrow(equipment_engine, actor_id: str) -> bool:
    """Consume one arrow from the actor's quiver (in off_hand).
    
    Called after bow attack to remove the used arrow.
    Arrows are consumed on attack (hit or miss).
    Quiver stays equipped even when empty (can be reloaded).
    
    Args:
        equipment_engine: Equipment engine instance
        actor_id: Actor using the bow
        
    Returns:
        bool: True if arrow was consumed, False if no arrow available
    """
    # Check off_hand for quiver (container system)
    quiver = equipment_engine.get_equipped_item(actor_id, "off_hand")
    if not quiver:
        return False
    
    # Verify it's a quiver
    from engine.items import get_item_definition
    quiver_id = quiver.get("item_id", "")
    quiver_def = get_item_definition(quiver_id)
    if not quiver_def or quiver_def.get("subtype") != "quiver":
        return False
    
    # Get current quantity from quiver
    quantity = quiver.get("quantity", 0)
    
    if quantity <= 0:
        # No arrows left
        return False
    else:
        # Decrease quantity (quiver stays equipped even at 0)
        quiver["quantity"] = quantity - 1
    
    return True


def get_armor_reduction(equipment_engine, actor_id: str, damage_type: str, actor_data: dict = None) -> float:
    """Get armor reduction for a damage type.

    New system: Armor provides percentage resistance by damage type.
    Formula: final_damage = raw_damage * (100 - resistance) / 100
    
    Includes durability scaling:
    effective_resistance = base_resistance * (durability / max_durability)

    Supports two sources of armor:
    1. Equipped armor items (checked first)
    2. Innate actor armor (fallback if no equipped armor, read from actor_data['armor'])
    """
    from engine.items import get_item_definition

    # First: check for equipped armor item
    if equipment_engine:
        equipped = equipment_engine.get_equipped_item(actor_id, "armor")
        if equipped:
            item_id = equipped.get("item_id", "")
            item_def = get_item_definition(item_id)
            if item_def:
                # Get base resistance from armor type
                armor_type = item_def.get("armor_type", "cloth")
                armor_data = item_def.get("armor", {})
                base_resistance = armor_data.get(armor_type, {}).get(damage_type, 0)

                # Apply durability scaling if available
                durability = equipped.get("durability", 100)
                max_durability = equipped.get("max_durability", 100)
                if max_durability > 0:
                    durability_multiplier = durability / max_durability
                    base_resistance = base_resistance * durability_multiplier

                # Convert percentage resistance to reduction (0.0 - 0.9)
                reduction = min(0.9, base_resistance / 100.0)
                return reduction

    # Second: check for innate actor armor (creatures' natural resistances)
    if actor_data:
        innate_armor = actor_data.get("armor", {})
        if innate_armor and isinstance(innate_armor, dict):
            base_resistance = innate_armor.get(damage_type, 0)
            # Scale down innate armor: values 1-100 map to ~0.01-0.5 reduction
            reduction = min(0.5, base_resistance / 100.0)
            return reduction

    return 0.0


def get_shield_absorption(equipment_engine, actor_id: str) -> int:
    """Get shield absorption value.

    Frozen design: Shields are separate from armor.
    Passive block: chance to reduce incoming damage, fixed absorption value.
    """
    from engine.items import get_item_definition

    equipped = equipment_engine.get_equipped_item(actor_id, "off_hand")
    if not equipped:
        return 0

    item_id = equipped.get("item_id", "")
    item_def = get_item_definition(item_id)
    if not item_def:
        return 0

    defense = item_def.get("defense", 0)
    return defense


def roll_shield_block(equipment_engine, actor_id: str) -> bool:
    """Roll for shield block.

    Frozen design: Passive block chance to reduce incoming damage.
    """
    from engine.items import get_item_definition

    equipped = equipment_engine.get_equipped_item(actor_id, "off_hand")
    if not equipped:
        return False

    item_id = equipped.get("item_id", "")
    item_def = get_item_definition(item_id)
    if not item_def:
        return False

    defense = item_def.get("defense", 0)
    block_chance = min(50, defense * 10)

    return random.randint(1, 100) <= block_chance


# ============ HIT RESOLUTION (Action Resolution Framework) ============


def resolve_attack(
    attacker: Dict[str, Any],
    target: Dict[str, Any],
    equipment_engine=None,
    action_config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Resolve an attack using the canonical action resolution framework.

    Formula: (Constructed Attribute + Technique + Modifiers) × BellCurveMultiplier

    Uses Action Definition System to determine which attributes are used.

    Supports both legacy (single attribute) and new (constructed_attribute) formats.
    Multi-attribute actions use weighted combination of base attributes.
    """
    from engine.action_resolution import resolve_opposed_action, OUTCOME_SUCCESS, OUTCOME_EXCEPTIONAL_SUCCESS

    weapon_info = get_weapon_damage(equipment_engine, attacker.get("id", "")) if equipment_engine else {
        "weapon": "unarmed",
        "damage_min": 5,
        "damage_max": 10,
        "damage_type": DAMAGE_BLUDGEONING,
    }

    # Use action config to determine attributes (support both old and new formats)
    if action_config:
        # Check for new constructed_attribute format
        if "constructed_attribute" in action_config:
            # New format: pass action definitions directly
            actor_action_def = {"constructed_attribute": action_config["constructed_attribute"]}
            target_action_def = {"constructed_attribute": {action_config.get("target_attribute", "observation"): 1.0}}
            
            result = resolve_opposed_action(
                actor=attacker,
                target=target,
                actor_attribute_name="observation",  # Ignored when action_definition provided
                target_attribute_name="observation",  # Ignored when action_definition provided
                actor_action_definition=actor_action_def,
                target_action_definition=target_action_def,
            )
        else:
            # Legacy format: use single attribute strings
            actor_attr = action_config.get("actor_attribute", "dexterity")
            target_attr = action_config.get("target_attribute", "observation")
            
            result = resolve_opposed_action(
                actor=attacker,
                target=target,
                actor_attribute_name=actor_attr,
                target_attribute_name=target_attr,
            )
    else:
        # Default: use dexterity vs observation
        result = resolve_opposed_action(
            actor=attacker,
            target=target,
            actor_attribute_name="dexterity",
            target_attribute_name="observation",
        )

    hit = result["outcome"] in (OUTCOME_SUCCESS, OUTCOME_EXCEPTIONAL_SUCCESS)

    return {
        "hit": hit,
        "outcome": result["outcome"],
        "margin": result["margin"],
        "actor_total": result["actor_total"],
        "target_total": result["target_total"],
        "multiplier": result["multiplier"],
        "weapon": weapon_info,
    }


# ============ ENGAGEMENT GRAPH ============


class EngagementGraph:
    """Simple engagement graph for combat groups."""

    def __init__(self):
        self._links: Dict[str, set] = {}

    def add_link(self, actor1: str, actor2: str):
        """Add an engagement link between two actors."""
        if actor1 not in self._links:
            self._links[actor1] = set()
        if actor2 not in self._links:
            self._links[actor2] = set()
        self._links[actor1].add(actor2)
        self._links[actor2].add(actor1)

    def remove_link(self, actor1: str, actor2: str):
        """Remove an engagement link between two actors."""
        if actor1 in self._links:
            self._links[actor1].discard(actor2)
        if actor2 in self._links:
            self._links[actor2].discard(actor1)

    def get_linked(self, actor_id: str) -> set:
        """Get all actors linked to an actor."""
        return self._links.get(actor_id, set())

    def get_group(self, actor_id: str) -> set:
        """Get the combat group for an actor (connected component)."""
        visited = set()
        stack = [actor_id]
        while stack:
            current = stack.pop()
            if current not in visited:
                visited.add(current)
                for linked in self._links.get(current, set()):
                    if linked not in visited:
                        stack.append(linked)
        return visited

    def are_in_same_group(self, actor1: str, actor2: str) -> bool:
        """Check if two actors are in the same combat group."""
        return actor2 in self.get_group(actor1)

    def has_link(self, actor1: str, actor2: str) -> bool:
        """Check if two actors are linked."""
        return actor2 in self._links.get(actor1, set())


# ============ COMBAT ENGINE ============


class CombatEngine:
    """Runtime combat engine for basic attacks."""

    def __init__(self):
        self._hp: Dict[str, Dict[str, int]] = {}
        self._actor_data: Dict[str, Dict[str, Any]] = {}
        self._engagement = EngagementGraph()
        self._events: List[Dict[str, Any]] = []
        self._attack_pressure: Dict[str, int] = {}  # Track attacks received per actor
        self._threat: Dict[str, Dict[str, int]] = {}  # target_id -> {actor_id: threat}

    def init_actor(self, actor_id: str, max_hp: int = DEFAULT_HP, actor_data: Optional[Dict] = None):
        """Initialize an actor's HP and optional data."""
        self._hp[actor_id] = {"current": max_hp, "max": max_hp}
        if actor_data:
            self._actor_data[actor_id] = actor_data

    def has_actor(self, actor_id: str) -> bool:
        """Check if an actor exists."""
        return actor_id in self._hp

    def has_effect(self, actor_id: str, effect_id: str) -> bool:
        """Check if an actor has a specific effect."""
        if hasattr(self, '_effects') and self._effects:
            return self._effects.has_effect(actor_id, effect_id)
        return False

    def get_actor_data(self, actor_id: str) -> Optional[Dict[str, Any]]:
        """Get actor data with attributes.
        
        Returns real actor data if set during init_actor.
        No placeholder fallback - data must be provided.
        """
        return self._actor_data.get(actor_id)

    def get_shield_absorption(self, actor_id: str) -> int:
        """Get shield absorption for an actor."""
        return get_shield_absorption(None, actor_id)

    def get_armor_reduction(self, actor_id: str, damage_type: str, actor_data: dict = None) -> float:
        """Get armor reduction for an actor."""
        return get_armor_reduction(None, actor_id, damage_type, actor_data=actor_data)

    def get_hp(self, actor_id: str) -> Dict[str, int]:
        """Get actor's HP."""
        return self._hp.get(actor_id, {"current": 0, "max": 0})

    def get_hp_state(self, actor_id: str) -> str:
        """Get actor's HP state."""
        hp = self._hp.get(actor_id, {"current": 0, "max": 0})
        return get_hp_state(hp["current"], hp["max"])

    def apply_damage(self, actor_id: str, damage: int) -> Dict[str, Any]:
        """Apply damage to an actor."""
        if actor_id not in self._hp:
            return {"error": "Actor not found"}

        hp = self._hp[actor_id]
        old_hp = hp["current"]
        hp["current"] = apply_damage(hp["current"], damage)
        new_state = get_hp_state(hp["current"], hp["max"])

        result = {
            "actor_id": actor_id,
            "old_hp": old_hp,
            "new_hp": hp["current"],
            "damage": damage,
            "state": new_state,
            "downed": is_downed(hp["current"]),
            "dead": is_dead(hp["current"]),
        }

        # Check death first, then downed
        if is_dead(hp["current"]) and not is_dead(old_hp):
            self._generate_event(EVENT_ACTOR_DIED, actor_id, 0)
            result["event"] = EVENT_ACTOR_DIED
            # Mark for graveyard respawn
            result["respawn"] = True
            result["respawn_location"] = {"map_id": "village", "node_id": "graveyard"}
        elif is_downed(hp["current"]) and not is_downed(old_hp):
            self._generate_event(EVENT_ACTOR_DOWNED, actor_id, 0)
            result["event"] = EVENT_ACTOR_DOWNED

        return result

    def get_engagement(self) -> EngagementGraph:
        """Get the engagement graph."""
        return self._engagement

    def get_combat_group(self, actor_id: str) -> set:
        """Get the combat group for an actor (connected component).
        
        Args:
            actor_id: Actor identifier
            
        Returns:
            Set of actor IDs in the same combat group
        """
        return self._engagement.get_group(actor_id)

    def get_all_combat_groups(self) -> List[set]:
        """Get all combat groups (all connected components).
        
        Returns:
            List of sets, each containing actor IDs in a group
        """
        visited = set()
        groups = []
        
        for actor_id in self._hp.keys():
            if actor_id not in visited:
                group = self._engagement.get_group(actor_id)
                groups.append(group)
                visited.update(group)
        
        return groups

    def is_same_combat_group(self, actor_a: str, actor_b: str) -> bool:
        """Check if two actors are in the same combat group.
        
        Args:
            actor_a: First actor identifier
            actor_b: Second actor identifier
            
        Returns:
            True if both actors are in the same combat group
        """
        return self._engagement.are_in_same_group(actor_a, actor_b)

    def attack(
        self,
        attacker_id: str,
        target_id: str,
        equipment_engine=None,
        current_tick: int = 0,
        attacker_data: Optional[Dict] = None,
        target_data: Optional[Dict] = None,
        action_config: Optional[Dict] = None,
        attack_profile: Optional[Dict] = None,
        weapon_damage: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a basic attack.

        Args:
            attacker_id: Attacker identifier
            target_id: Target identifier
            equipment_engine: EquipmentEngine instance
            current_tick: Current world tick
            attacker_data: Real attacker data with attributes (required)
            target_data: Real target data with attributes (required)
            action_config: Action definition config for attribute mapping
            attack_profile: Attack profile dict (optional, uses weapon if not provided)
        """
        attacker_hp = self._hp.get(attacker_id, {"current": 0, "max": 0})
        if is_downed(attacker_hp["current"]):
            return {"success": False, "message": "You are downed and cannot attack."}

        target_hp = self._hp.get(target_id, {"current": 0, "max": 0})
        if is_downed(target_hp["current"]):
            return {"success": False, "message": f"{target_id} is already downed."}

        self._generate_event(EVENT_ATTACK_STARTED, attacker_id, current_tick, target_id=target_id)

        # Track attack pressure (how many times target has been TARGETED, not just hit)
        if target_id not in self._attack_pressure:
            self._attack_pressure[target_id] = 0
        self._attack_pressure[target_id] += 1

        # Get attack profile
        if attack_profile:
            profile = attack_profile
        elif equipment_engine:
            profile = get_weapon_attack_profile(equipment_engine, attacker_id)
        else:
            profile = ATTACK_PROFILES["unarmed"]

        # Validate ranged weapon has arrow equipped
        if profile.get("is_ranged", False) and equipment_engine:
            arrow_damage = get_arrow_damage(equipment_engine, attacker_id)
            if arrow_damage == 0:
                return {
                    "success": False,
                    "message": f"{attacker_id} cannot use {profile['name']} without an arrow equipped!",
                }

        # Validate ranged targeting: cannot target own combat group
        if profile.get("targeting_mode") == TARGETING_RANGED:
            if self.is_same_combat_group(attacker_id, target_id):
                return {
                    "success": False,
                    "message": f"{attacker_id} cannot target {target_id} - they are in the same combat group!",
                }

        # Require real actor data - no placeholder attributes
        if not attacker_data:
            return {"success": False, "message": "Attacker data required. No placeholder attributes allowed."}
        if not target_data:
            return {"success": False, "message": "Target data required. No placeholder attributes allowed."}

        attacker_dict = attacker_data
        target_dict = target_data

        # Build action config from profile
        if not action_config:
            # Use constructed_attribute from profile (new format)
            action_config = {
                "constructed_attribute": profile["constructed_attribute"],
                "target_attribute": "observation",
            }

        resolution = resolve_attack(attacker_dict, target_dict, equipment_engine, action_config)
        hit = resolution["hit"]

        if not hit:
            self._generate_event(EVENT_ATTACK_MISSED, attacker_id, current_tick, target_id=target_id)
            # Build message with display names
            attacker_name = attacker_data.get('name', attacker_id) if attacker_data else attacker_id
            target_name = target_data.get('name', target_id) if target_data else target_id
            return {
                "success": True,
                "hit": False,
                "message": f"{attacker_name} attacks {target_name} but misses!",
                "weapon": profile["name"],
                "resolution": resolution,
            }

        # Calculate damage from weapon (if provided) or profile
        if weapon_damage is not None:
            base_damage = weapon_damage
        else:
            base_damage = profile["base_damage"]
        damage_type = profile["damage_type"]
        
        # For ranged weapons (bow), add arrow damage if available
        if profile.get("is_ranged", False) and equipment_engine:
            arrow_damage = get_arrow_damage(equipment_engine, attacker_id)
            if arrow_damage > 0:
                base_damage += arrow_damage
        
        # Apply constructed attribute damage bonus if enabled
        if profile.get("apply_attribute_damage_bonus", False):
            from engine.action_resolution import calculate_constructed_attribute, get_damage_modifier
            constructed_attr = calculate_constructed_attribute(attacker_dict, profile["constructed_attribute"])
            damage_modifier = get_damage_modifier(constructed_attr)
            base_damage += damage_modifier

        # Get shield block
        shield_blocked = roll_shield_block(equipment_engine, target_id) if equipment_engine else False
        shield_abs = get_shield_absorption(equipment_engine, target_id) if equipment_engine else 0
        if not shield_blocked:
            shield_abs = 0

        # Get armor reduction (checks equipped armor first, then innate actor armor)
        armor_red = get_armor_reduction(equipment_engine, target_id, damage_type, actor_data=target_data)
        
        # Get damage reduction from threat (0.1 per 100 threat = 10% per 100 threat)
        threat_reduction = self.get_damage_reduction(target_id, attacker_id)

        # Calculate final damage
        damage_result = calculate_damage(base_damage, damage_type, shield_abs, armor_red)
        
        # Apply threat-based damage reduction
        if threat_reduction > 0:
            damage_result["hp_damage"] = int(damage_result["hp_damage"] * (1.0 - threat_reduction))
            damage_result["threat_reduction"] = threat_reduction

        # Apply damage
        damage_apply = self.apply_damage(target_id, damage_result["hp_damage"])

        # Generate hit event
        self._generate_event(EVENT_ATTACK_HIT, attacker_id, current_tick, target_id=target_id, data=damage_result)

        # Add engagement link only for melee attacks
        if profile.get("is_melee", True):
            self._engagement.add_link(attacker_id, target_id)

        # Add threat (damage = threat amount)
        self.add_threat(target_id, attacker_id, damage_result["hp_damage"])

        # Consume arrow for ranged attacks
        if profile.get("is_ranged", False) and equipment_engine:
            consume_arrow(equipment_engine, attacker_id)

        # Build message with display names
        attacker_name = attacker_data.get('name', attacker_id) if attacker_data else attacker_id
        target_name = target_data.get('name', target_id) if target_data else target_id
        msg = f"{attacker_name} uses {profile['name']} on {target_name} for {damage_result['hp_damage']} damage!"
        if damage_apply.get("downed"):
            msg += f" {target_name} is downed!"
        elif damage_apply.get("dead"):
            msg += f" {target_name} is dead!"

        return {
            "success": True,
            "hit": True,
            "message": msg,
            "weapon": profile["name"],
            "damage": damage_result,
            "target_hp": damage_apply,
            "resolution": resolution,
        }

    def add_threat(self, target_id: str, attacker_id: str, amount: int):
        """Add threat to a target from an attacker."""
        if target_id not in self._threat:
            self._threat[target_id] = {}
        if attacker_id not in self._threat[target_id]:
            self._threat[target_id][attacker_id] = 0
        self._threat[target_id][attacker_id] += amount

    def add_taunt(self, target_id: str, attacker_id: str, taunt_amount: int = 300):
        """Add taunt threat (instant +300, decays -100 per tick)."""
        self.add_threat(target_id, attacker_id, taunt_amount)

    def decay_threat(self, target_id: str, decay_amount: int = 100):
        """Decay all taunt threat on a target."""
        if target_id not in self._threat:
            return
        for attacker_id in list(self._threat[target_id].keys()):
            current_threat = self._threat[target_id][attacker_id]
            new_threat = max(0, current_threat - decay_amount)
            if new_threat == 0:
                del self._threat[target_id][attacker_id]
            else:
                self._threat[target_id][attacker_id] = new_threat

    def get_highest_threat(self, target_id: str) -> tuple[str, int]:
        """Get the attacker with highest threat on a target.
        
        Returns:
            Tuple of (attacker_id, threat_amount)
        """
        if target_id not in self._threat or not self._threat[target_id]:
            return ("", 0)
        
        highest_attacker = max(self._threat[target_id], key=self._threat[target_id].get)
        highest_threat = self._threat[target_id][highest_attacker]
        return (highest_attacker, highest_threat)

    def get_threat(self, target_id: str, attacker_id: str) -> int:
        """Get threat amount from a specific attacker on a target."""
        return self._threat.get(target_id, {}).get(attacker_id, 0)

    def get_damage_reduction(self, target_id: str, attacker_id: str) -> float:
        """Get damage reduction based on threat.
        
        Formula: 0.05 per 100 threat (max 0.9 = 90% reduction)
        """
        threat = self.get_threat(target_id, attacker_id)
        reduction = min(0.9, (threat / 100) * 0.05)
        return reduction

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all generated events."""
        return list(self._events)

    def clear_events(self):
        """Clear all events."""
        self._events.clear()

    def _generate_event(
        self,
        event_type: str,
        actor_id: str,
        tick: int,
        target_id: str = "",
        data: Optional[Dict] = None,
    ):
        """Generate a combat event."""
        event = {
            "event_type": event_type,
            "actor_id": actor_id,
            "target_id": target_id,
            "tick": tick,
            "timestamp": time.time(),
            "data": data or {},
        }
        self._events.append(event)