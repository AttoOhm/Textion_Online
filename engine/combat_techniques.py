"""
Combat Techniques Integration (Phase 6E)

Implements the first vertical slice of combat techniques.

Uses existing systems:
- Character Foundation
- Techniques
- Long Actions
- Action Definitions
- Action Resolution
- Combat Engine
- Effects
- Cooldowns
- Engagement Graph

Implements only:
- Shield Bash
- Backstab
- Death Mark
- Track Prey

No full technique catalog. No magic disciplines. No combat AI.
"""

import random
import time
from typing import Optional, Dict, List, Any

# ============ CONSTANTS ============

# Technique IDs
TECHNIQUE_SHIELD_BASH = "shield_bash"
TECHNIQUE_BACKSTAB = "backstab"
TECHNIQUE_DEATH_MARK = "death_mark"
TECHNIQUE_TRACK_PREY = "track_prey"
TECHNIQUE_ALERT = "alert"
TECHNIQUE_POWER_STRIKE = "power_strike"
TECHNIQUE_FORGE_MASTERY = "forge_mastery"

# Creature Techniques (shared by wolves, goblins, etc.)
TECHNIQUE_BITE = "bite"
TECHNIQUE_CLAW = "claw"
TECHNIQUE_HOWL = "howl"
TECHNIQUE_SHORT_BOW_SHOT = "short_bow_shot"
TECHNIQUE_MELEE_ATTACK = "melee_attack"
TECHNIQUE_CRUNCH = "crunch"
TECHNIQUE_DOUBLE_ATTACK = "double_attack"

# Sword Techniques (taught by Aldric)
TECHNIQUE_DRAW_CUT = "draw_cut"
TECHNIQUE_RIPOSTE = "riposte"
TECHNIQUE_SWORD_DANCE = "sword_dance"
TECHNIQUE_PERFECT_CUT = "perfect_cut"
TECHNIQUE_WHIRLWIND = "whirlwind"

# Effect IDs
EFFECT_STUNNED = "stunned"
EFFECT_DEATH_MARK = "death_mark"
EFFECT_TAUNT = "taunt"
EFFECT_MANA_SHIELD = "mana_shield"
EFFECT_ARCANE_SIGHT = "arcane_sight"
EFFECT_DIVINE_SHIELD = "divine_shield"
EFFECT_BLESSED = "blessed"

# Divine Technique IDs
TECHNIQUE_BLESS = "bless"
TECHNIQUE_PURIFY = "purify"
TECHNIQUE_DIVINE_SHIELD = "divine_shield"
TECHNIQUE_HOLY_LIGHT = "holy_light"
TECHNIQUE_RESURRECTION = "resurrection"

# Hunter Technique IDs
TECHNIQUE_DEATH_MARK = "death_mark"
TECHNIQUE_TRACK_PREY = "track_prey"
TECHNIQUE_BEAR_TRAP = "bear_trap"
TECHNIQUE_SILENT_STEP = "silent_step"
TECHNIQUE_LARGE_TRAP = "large_trap"
TECHNIQUE_PACIFY_PREY = "pacify_prey"
TECHNIQUE_LOOT = "loot"

# Arcane Technique IDs
TECHNIQUE_MAGIC_MISSILE = "magic_missile"
TECHNIQUE_MANA_SHIELD = "mana_shield"
TECHNIQUE_TELEPORT = "teleport"
TECHNIQUE_ARCANE_SIGHT = "arcane_sight"
TECHNIQUE_ARCANE_EXPLOSION = "arcane_explosion"
TECHNIQUE_REALITY_TEAR = "reality_tear"

# Event types
EVENT_TECHNIQUE_USED = "technique_used"
EVENT_TECHNIQUE_COOLDOWN = "technique_cooldown"
EVENT_TECHNIQUE_FAILED = "technique_failed"

# ============ TECHNIQUE DEFINITIONS ============

TECHNIQUE_DEFINITIONS = {
    TECHNIQUE_SHIELD_BASH: {
        "id": TECHNIQUE_SHIELD_BASH,
        "name": "Shield Bash",
        "discipline": "Shieldcraft",
        "category": "Defense",
        "duration": 1,
        "cooldown": 2,
        "description": "Bash with shield, applying Stunned (1 tick)",
        "actor_attribute": "strength",
        "target_attribute": "observation",
        "base_damage": {"min": 3, "max": 7},
        "effect": {
            "effect_id": EFFECT_STUNNED,
            "duration": 1,
            "duration_type": "timed",
        },
    },
    TECHNIQUE_BACKSTAB: {
        "id": TECHNIQUE_BACKSTAB,
        "name": "Backstab",
        "discipline": "Assassination",
        "category": "Attack",
        "duration": 1,
        "cooldown": 2,
        "description": "Bonus damage if target not engaged with attacker",
        "actor_attribute": "dexterity",
        "target_attribute": "observation",
        "bonus_damage": 1.5,
        "requirement": "target_not_engaged",
    },
    TECHNIQUE_DEATH_MARK: {
        "id": TECHNIQUE_DEATH_MARK,
        "name": "Death Mark",
        "discipline": "Assassination",
        "category": "Support",
        "duration": 1,
        "cooldown": 10,
        "description": "Mark target for death, increasing future damage",
        "actor_attribute": "willpower",
        "target_attribute": "observation",
        "effect": {
            "effect_id": EFFECT_DEATH_MARK,
            "duration": 10,
            "duration_type": "timed",
        },
    },
    TECHNIQUE_TRACK_PREY: {
        "id": TECHNIQUE_TRACK_PREY,
        "name": "Track Prey",
        "discipline": "Hunting",
        "category": "Support",
        "duration": 2,
        "cooldown": 0,
        "description": "Track target, providing information",
        "actor_attribute": "observation",
        "target_attribute": "observation",
    },
    TECHNIQUE_ALERT: {
        "id": TECHNIQUE_ALERT,
        "name": "Alert",
        "discipline": "Awareness",
        "category": "Support",
        "duration": 0,
        "cooldown": 5,
        "description": "Heighten awareness, improving perception temporarily",
        "actor_attribute": "observation",
        "target_attribute": "observation",
        "effect": {
            "effect_id": "alert_buff",
            "duration": 10,
            "duration_type": "timed",
        },
    },
    TECHNIQUE_POWER_STRIKE: {
        "id": TECHNIQUE_POWER_STRIKE,
        "name": "Power Strike",
        "discipline": "Smithing",
        "category": "Attack",
        "duration": 2,
        "cooldown": 3,
        "description": "A powerful strike dealing extra damage",
        "actor_attribute": "strength",
        "target_attribute": "constitution",
        "bonus_damage": 1.5,
    },
    TECHNIQUE_FORGE_MASTERY: {
        "id": TECHNIQUE_FORGE_MASTERY,
        "name": "Forge Mastery",
        "discipline": "Smithing",
        "category": "Support",
        "duration": 1,
        "cooldown": 10,
        "description": "Masterful forging technique for superior items",
        "actor_attribute": "knowledge",
        "target_attribute": "knowledge",
        "effect": {
            "effect_id": "forge_mastery_buff",
            "duration": 5,
            "duration_type": "timed",
        },
    },
    # ============ SWORD TECHNIQUES ============
    TECHNIQUE_DRAW_CUT: {
        "id": TECHNIQUE_DRAW_CUT,
        "name": "Draw Cut",
        "discipline": "Swordsmanship",
        "category": "Attack",
        "duration": 1,
        "cooldown": 3,
        "description": "A swift drawing cut. Bonus damage if target is marked. Requires sword equipped.",
        "actor_attribute": "dexterity",
        "target_attribute": "observation",
        "base_damage": {"min": 8, "max": 15},
        "bonus_vs_marked": 2.0,
        "requires_weapon": "sword",
        "reactiveness_bonus": 30,
    },
    TECHNIQUE_RIPOSTE: {
        "id": TECHNIQUE_RIPOSTE,
        "name": "Riposte",
        "discipline": "Swordsmanship",
        "category": "Attack",
        "duration": 1,
        "cooldown": 2,
        "description": "A counter-attack that taunts the target",
        "actor_attribute": "dexterity",
        "target_attribute": "observation",
        "base_damage": {"min": 5, "max": 10},
        "taunt_amount": 300,
        "requires_weapon": "sword",
    },
    TECHNIQUE_SWORD_DANCE: {
        "id": TECHNIQUE_SWORD_DANCE,
        "name": "Sword Dance",
        "discipline": "Swordsmanship",
        "category": "Attack",
        "duration": 3,
        "cooldown": 8,
        "description": "A complex 3-step sequence. Each step requires different input. Final step hits 3 targets.",
        "actor_attribute": "dexterity",
        "target_attribute": "observation",
        "base_damage": {"min": 4, "max": 8},
        "final_damage": {"min": 10, "max": 18},
        "taunt_amount": 300,
        "requires_weapon": "sword",
        "multi_stage": True,
        "stages": 3,
    },
    TECHNIQUE_PERFECT_CUT: {
        "id": TECHNIQUE_PERFECT_CUT,
        "name": "Perfect Cut",
        "discipline": "Swordsmanship",
        "category": "Attack",
        "duration": 2,
        "cooldown": 5,
        "description": "A precisely aimed strike that bypasses armor",
        "actor_attribute": "dexterity",
        "target_attribute": "observation",
        "base_damage": {"min": 12, "max": 20},
        "armor_penetration": 0.5,
        "requires_weapon": "sword",
    },
    TECHNIQUE_WHIRLWIND: {
        "id": TECHNIQUE_WHIRLWIND,
        "name": "Whirlwind",
        "discipline": "Swordsmanship",
        "category": "Attack",
        "duration": 2,
        "cooldown": 6,
        "description": "A spinning attack that hits all nearby enemies and stuns them",
        "actor_attribute": "strength",
        "target_attribute": "constitution",
        "base_damage": {"min": 6, "max": 12},
        "stun_duration": 1,
        "requires_weapon": "sword",
        "target_scope": "node",
    },
    # ============ CREATURE TECHNIQUES ============
    TECHNIQUE_BITE: {
        "id": TECHNIQUE_BITE,
        "name": "Bite",
        "discipline": "Natural",
        "category": "Attack",
        "duration": 1,
        "cooldown": 2,
        "description": "Bite the target with sharp teeth",
        "actor_attribute": "strength",
        "target_attribute": "constitution",
        "base_damage": {"min": 3, "max": 8},
    },
    TECHNIQUE_CLAW: {
        "id": TECHNIQUE_CLAW,
        "name": "Claw",
        "discipline": "Natural",
        "category": "Attack",
        "duration": 1,
        "cooldown": 1,
        "description": "Slash with claws",
        "actor_attribute": "dexterity",
        "target_attribute": "observation",
        "base_damage": {"min": 2, "max": 6},
    },
    TECHNIQUE_HOWL: {
        "id": TECHNIQUE_HOWL,
        "name": "Howl",
        "discipline": "Natural",
        "category": "Support",
        "duration": 1,
        "cooldown": 5,
        "description": "Howl to boost own attack power and allies of same type",
        "actor_attribute": "willpower",
        "target_attribute": "willpower",
        "effect": {
            "effect_id": "howl_buff",
            "duration": 10,
            "duration_type": "timed",
        },
        "buff_self": True,
        "buff_allies": True,
        "buff_stat": "strength",
        "buff_formula": "willpower / 10",
    },
    # ============ NEW: RANGED AND MELEE CREATURE TECHNIQUES ============
    TECHNIQUE_SHORT_BOW_SHOT: {
        "id": TECHNIQUE_SHORT_BOW_SHOT,
        "name": "Short Bow Shot",
        "discipline": "Natural",
        "category": "Attack",
        "duration": 1,
        "cooldown": 2,
        "description": "Fire an arrow from a short bow at range",
        "actor_attribute": "dexterity",
        "target_attribute": "reactiveness",
        "base_damage": {"min": 5, "max": 12},
        "is_ranged": True,
    },
    TECHNIQUE_MELEE_ATTACK: {
        "id": TECHNIQUE_MELEE_ATTACK,
        "name": "Melee Attack",
        "discipline": "Natural",
        "category": "Attack",
        "duration": 1,
        "cooldown": 1,
        "description": "A basic melee attack with whatever weapon is at hand",
        "actor_attribute": "strength",
        "target_attribute": "constitution",
        "base_damage": {"min": 3, "max": 8},
        "is_melee": True,
    },
    TECHNIQUE_CRUNCH: {
        "id": TECHNIQUE_CRUNCH,
        "name": "Crunch",
        "discipline": "Natural",
        "category": "Attack",
        "duration": 2,
        "cooldown": 3,
        "description": "A powerful crushing bite or club strike",
        "actor_attribute": "strength",
        "target_attribute": "constitution",
        "base_damage": {"min": 8, "max": 15},
    },
    TECHNIQUE_DOUBLE_ATTACK: {
        "id": TECHNIQUE_DOUBLE_ATTACK,
        "name": "Double Attack",
        "discipline": "Natural",
        "category": "Attack",
        "duration": 1,
        "cooldown": 3,
        "description": "Attack twice in one swift motion",
        "actor_attribute": "strength",
        "target_attribute": "constitution",
        "base_damage": {"min": 6, "max": 12},
        "double_strike": True,
    },
    # ============ ARCANE TECHNIQUES ============
    TECHNIQUE_MAGIC_MISSILE: {
        "id": TECHNIQUE_MAGIC_MISSILE,
        "name": "Magic Missile",
        "discipline": "Arcane",
        "category": "Attack",
        "duration": 1,
        "cooldown": 2,
        "description": "Launch a bolt of arcane energy that always hits",
        "actor_attribute": "arcana",
        "target_attribute": "constitution",
        "base_damage": {"min": 10, "max": 18},
        "requires_arcane_focus": True,
        "runestone_cost": 1,
        "accuracy": 1.0,
    },
    TECHNIQUE_MANA_SHIELD: {
        "id": TECHNIQUE_MANA_SHIELD,
        "name": "Mana Shield",
        "discipline": "Arcane",
        "category": "Defense",
        "duration": 5,
        "cooldown": 8,
        "description": "Create a protective barrier of arcane energy",
        "actor_attribute": "arcana",
        "target_attribute": "willpower",
        "effect": {
            "effect_id": EFFECT_MANA_SHIELD,
            "duration": 5,
            "duration_type": "timed",
        },
        "requires_arcane_focus": True,
        "runestone_cost": 2,
        "shield_amount": 30,
    },
    TECHNIQUE_TELEPORT: {
        "id": TECHNIQUE_TELEPORT,
        "name": "Teleport",
        "discipline": "Arcane",
        "category": "Movement",
        "duration": 1,
        "cooldown": 5,
        "description": "Instantly teleport a short distance",
        "actor_attribute": "arcana",
        "target_attribute": "arcana",
        "requires_arcane_focus": True,
        "runestone_cost": 1,
        "teleport_distance": 5,
    },
    TECHNIQUE_ARCANE_SIGHT: {
        "id": TECHNIQUE_ARCANE_SIGHT,
        "name": "Arcane Sight",
        "discipline": "Arcane",
        "category": "Support",
        "duration": 10,
        "cooldown": 15,
        "description": "Reveal hidden magic and enhance perception",
        "actor_attribute": "arcana",
        "target_attribute": "observation",
        "effect": {
            "effect_id": EFFECT_ARCANE_SIGHT,
            "duration": 10,
            "duration_type": "timed",
        },
        "requires_arcane_focus": True,
        "runestone_cost": 1,
        "perception_boost": 50,
    },
    TECHNIQUE_ARCANE_EXPLOSION: {
        "id": TECHNIQUE_ARCANE_EXPLOSION,
        "name": "Arcane Explosion",
        "discipline": "Arcane",
        "category": "Attack",
        "duration": 2,
        "cooldown": 6,
        "description": "Unleash a burst of arcane energy hitting all nearby enemies",
        "actor_attribute": "arcana",
        "target_attribute": "constitution",
        "base_damage": {"min": 15, "max": 25},
        "requires_arcane_focus": True,
        "runestone_cost": 3,
        "target_scope": "node",
    },
    TECHNIQUE_REALITY_TEAR: {
        "id": TECHNIQUE_REALITY_TEAR,
        "name": "Reality Tear",
        "discipline": "Arcane",
        "category": "Attack",
        "duration": 3,
        "cooldown": 10,
        "description": "Tear a rift in reality, dealing massive damage to a single target",
        "actor_attribute": "arcana",
        "target_attribute": "constitution",
        "base_damage": {"min": 40, "max": 60},
        "requires_arcane_focus": True,
        "runestone_cost": 5,
        "armor_penetration": 0.75,
    },
    # ============ DIVINE TECHNIQUES ============
    TECHNIQUE_BLESS: {
        "id": TECHNIQUE_BLESS,
        "name": "Bless",
        "discipline": "Divine",
        "category": "Support",
        "duration": 0,
        "cooldown": 5,
        "description": "Bless a target, enhancing their combat abilities",
        "actor_attribute": "willpower",
        "target_attribute": "willpower",
        "effect": {
            "effect_id": EFFECT_BLESSED,
            "duration": 10,
            "duration_type": "timed",
        },
        "requires_holy_symbol": True,
        "holy_water_cost": 1,
    },
    TECHNIQUE_PURIFY: {
        "id": TECHNIQUE_PURIFY,
        "name": "Purify",
        "discipline": "Divine",
        "category": "Support",
        "duration": 1,
        "cooldown": 3,
        "description": "Remove negative effects from target",
        "actor_attribute": "willpower",
        "target_attribute": "willpower",
        "requires_holy_symbol": True,
        "holy_water_cost": 1,
    },
    TECHNIQUE_DIVINE_SHIELD: {
        "id": TECHNIQUE_DIVINE_SHIELD,
        "name": "Divine Shield",
        "discipline": "Divine",
        "category": "Defense",
        "duration": 5,
        "cooldown": 10,
        "description": "Create a holy barrier that absorbs damage",
        "actor_attribute": "willpower",
        "target_attribute": "willpower",
        "effect": {
            "effect_id": EFFECT_DIVINE_SHIELD,
            "duration": 5,
            "duration_type": "timed",
        },
        "requires_holy_symbol": True,
        "holy_water_cost": 2,
        "shield_amount": 40,
    },
    TECHNIQUE_HOLY_LIGHT: {
        "id": TECHNIQUE_HOLY_LIGHT,
        "name": "Holy Light",
        "discipline": "Divine",
        "category": "Attack",
        "duration": 1,
        "cooldown": 4,
        "description": "Call down holy light to damage undead and demons",
        "actor_attribute": "willpower",
        "target_attribute": "constitution",
        "base_damage": {"min": 15, "max": 25},
        "requires_holy_symbol": True,
        "holy_water_cost": 1,
        "bonus_vs_undead": 2.0,
    },
    TECHNIQUE_RESURRECTION: {
        "id": TECHNIQUE_RESURRECTION,
        "name": "Resurrection",
        "discipline": "Divine",
        "category": "Support",
        "duration": 3,
        "cooldown": 20,
        "description": "Restore a fallen ally to life",
        "actor_attribute": "willpower",
        "target_attribute": "willpower",
        "requires_holy_symbol": True,
        "holy_water_cost": 5,
    },
    # ============ HUNTER TECHNIQUES ============
    TECHNIQUE_DEATH_MARK: {
        "id": TECHNIQUE_DEATH_MARK,
        "name": "Death Mark",
        "discipline": "Hunting",
        "category": "Support",
        "duration": 1,
        "cooldown": 10,
        "description": "Mark target for death, increasing future damage",
        "actor_attribute": "willpower",
        "target_attribute": "observation",
        "effect": {
            "effect_id": EFFECT_DEATH_MARK,
            "duration": 10,
            "duration_type": "timed",
        },
    },
    TECHNIQUE_TRACK_PREY: {
        "id": TECHNIQUE_TRACK_PREY,
        "name": "Track Prey",
        "discipline": "Hunting",
        "category": "Support",
        "duration": 2,
        "cooldown": 0,
        "description": "Track target, providing information",
        "actor_attribute": "observation",
        "target_attribute": "observation",
    },
    TECHNIQUE_BEAR_TRAP: {
        "id": TECHNIQUE_BEAR_TRAP,
        "name": "Bear Trap",
        "discipline": "Hunting",
        "category": "Trap",
        "duration": 0,
        "cooldown": 5,
        "description": "Place a bear trap that immobilizes targets",
        "actor_attribute": "knowledge",
        "target_attribute": "constitution",
        "trap_damage": {"min": 10, "max": 20},
        "trap_effect": "immobilized",
        "trap_duration": 3,
    },
    TECHNIQUE_SILENT_STEP: {
        "id": TECHNIQUE_SILENT_STEP,
        "name": "Silent Step",
        "discipline": "Hunting",
        "category": "Stealth",
        "duration": 5,
        "cooldown": 10,
        "description": "Move silently, reducing detection chance",
        "actor_attribute": "dexterity",
        "target_attribute": "observation",
        "effect": {
            "effect_id": "silent_step",
            "duration": 5,
            "duration_type": "timed",
        },
    },
    TECHNIQUE_LARGE_TRAP: {
        "id": TECHNIQUE_LARGE_TRAP,
        "name": "Large Trap",
        "discipline": "Hunting",
        "category": "Trap",
        "duration": 0,
        "cooldown": 8,
        "description": "Place a large trap that hits multiple targets",
        "actor_attribute": "knowledge",
        "target_attribute": "constitution",
        "trap_damage": {"min": 15, "max": 25},
        "trap_effect": "immobilized",
        "trap_duration": 4,
        "target_scope": "node",
    },
    TECHNIQUE_PACIFY_PREY: {
        "id": TECHNIQUE_PACIFY_PREY,
        "name": "Pacify Prey",
        "discipline": "Hunting",
        "category": "Support",
        "duration": 1,
        "cooldown": 5,
        "description": "Calm an aggressive creature, making it non-hostile",
        "actor_attribute": "willpower",
        "target_attribute": "willpower",
        "effect": {
            "effect_id": "pacified",
            "duration": 20,
            "duration_type": "timed",
        },
    },
    TECHNIQUE_LOOT: {
        "id": TECHNIQUE_LOOT,
        "name": "Loot",
        "discipline": "Hunting",
        "category": "Utility",
        "duration": 1,
        "cooldown": 0,
        "description": "Quickly loot a corpse, taking all available items",
        "actor_attribute": "dexterity",
        "target_attribute": "dexterity",
    },
}


# ============ COOLDOWN TRACKER ============


class CooldownTracker:
    """Tracks technique cooldowns for all actors."""

    def __init__(self):
        self._cooldowns: Dict[str, Dict[str, int]] = {}  # actor_id -> {technique_id: last_used_tick}

    def can_use(self, actor_id: str, technique_id: str, current_tick: int) -> bool:
        """Check if actor can use a technique."""
        if actor_id not in self._cooldowns:
            return True
        if technique_id not in self._cooldowns[actor_id]:
            return True

        last_used = self._cooldowns[actor_id][technique_id]
        cooldown = TECHNIQUE_DEFINITIONS.get(technique_id, {}).get("cooldown", 0)
        return current_tick >= last_used + cooldown

    def use_technique(self, actor_id: str, technique_id: str, current_tick: int):
        """Record technique usage. Cooldown begins when technique completes."""
        if actor_id not in self._cooldowns:
            self._cooldowns[actor_id] = {}
        self._cooldowns[actor_id][technique_id] = current_tick

    def get_remaining(self, actor_id: str, technique_id: str, current_tick: int) -> int:
        """Get remaining cooldown ticks."""
        if actor_id not in self._cooldowns:
            return 0
        if technique_id not in self._cooldowns[actor_id]:
            return 0

        last_used = self._cooldowns[actor_id][technique_id]
        cooldown = TECHNIQUE_DEFINITIONS.get(technique_id, {}).get("cooldown", 0)
        remaining = cooldown - (current_tick - last_used)
        return max(0, remaining)


# ============ COMBAT TECHNIQUE ENGINE ============


class CombatTechniqueEngine:
    """Runtime combat technique engine.

    Integrates techniques with combat pipeline.
    Uses Long Actions for proper timing.
    """

    def __init__(self, combat_engine, technique_manager, effect_engine, action_queue):
        self._combat = combat_engine
        self._techniques = technique_manager
        self._effects = effect_engine
        self._actions = action_queue
        self._cooldowns = CooldownTracker()
        self._events: List[Dict[str, Any]] = []
        self._pending_techniques: Dict[str, Dict] = {}  # action_id -> technique info

    def use_technique(
        self,
        actor_id: str,
        technique_id: str,
        target_id: str,
        actor_data: Dict,
        target_data: Dict,
        equipment_engine=None,
        current_tick: int = 0,
        instant: bool = False,
    ) -> Dict[str, Any]:
        """Use a combat technique.

        If instant=True, resolves immediately (for AI creatures).
        Otherwise creates a long action and waits for duration before resolving.
        """
        # Check if technique exists
        if technique_id not in TECHNIQUE_DEFINITIONS:
            return {"success": False, "message": f"Unknown technique: {technique_id}"}

        # Check if actor has learned the technique
        if not self._techniques.has_technique(actor_id, technique_id):
            return {"success": False, "message": f"Technique not learned: {technique_id}"}

        # Check cooldown
        if not self._cooldowns.can_use(actor_id, technique_id, current_tick):
            remaining = self._cooldowns.get_remaining(actor_id, technique_id, current_tick)
            return {"success": False, "message": f"Technique on cooldown: {remaining} ticks remaining"}

        # Check if actor is downed (skip for AI creatures - they manage their own HP)
        # Only check for players who have the downed state
        if actor_data.get('type') != 'creature':
            # For players/NPCs, check combat engine
            actor_hp = self._combat.get_hp(actor_id)
            if actor_hp["current"] <= 0:
                return {"success": False, "message": "You are downed and cannot use techniques."}

        # Check if target is downed (skip for AI creatures)
        target_data_hp = target_data.get('hp', 100)
        if target_data_hp <= 0 and target_data.get('type') == 'creature':
            return {"success": False, "message": "Target is already downed."}

        # Check if actor is stunned
        if self._effects.has_effect(actor_id, EFFECT_STUNNED):
            return {"success": False, "message": "You are stunned and cannot use techniques."}

        # Get technique definition
        tech_def = TECHNIQUE_DEFINITIONS[technique_id]
        
        # For AI creatures, resolve instantly instead of queuing
        if instant:
            result = self._resolve_technique(
                actor_id=actor_id,
                target_id=target_id,
                technique_id=technique_id,
                actor_data=actor_data,
                target_data=target_data,
                equipment_engine=equipment_engine,
                current_tick=current_tick,
            )
            # Record cooldown
            self._cooldowns.use_technique(actor_id, technique_id, current_tick)
            return result
        
        # Queue the action (creates a single action in the queue)
        action = self._actions.queue_action(
            actor_id=actor_id,
            action_type=f"technique_{technique_id}",
            duration_ticks=tech_def["duration"],
            current_tick=current_tick,
            target={"id": target_id},
            parameters={"technique_id": technique_id},
            resolution_config={
                "actor_attribute": tech_def["actor_attribute"],
                "target_attribute": tech_def["target_attribute"],
            },
        )
        
        if not action:
            return {"success": False, "message": "Actor already has an active action."}

        # Store pending technique info using the queued action's ID
        self._pending_techniques[action["action_id"]] = {
            "actor_id": actor_id,
            "target_id": target_id,
            "technique_id": technique_id,
            "actor_data": actor_data,
            "target_data": target_data,
            "equipment_engine": equipment_engine,
        }

        # Generate event
        self._generate_event(EVENT_TECHNIQUE_USED, actor_id, current_tick, target_id=target_id, data={"technique_id": technique_id, "status": "queued"})

        # Build message with display names
        actor_name = actor_data.get('name', actor_id) if actor_data else actor_id
        target_name = target_data.get('name', target_id) if target_data else target_id

        return {
            "success": True,
            "hit": False,
            "technique": technique_id,
            "message": f"{actor_name} starts {tech_def['name']} on {target_name}!",
            "action_id": action["action_id"],
            "duration": tech_def["duration"],
        }

    def resolve_technique(self, action_id: str, current_tick: int) -> Dict[str, Any]:
        """Resolve a completed technique after long action finishes."""
        if action_id not in self._pending_techniques:
            return {"success": False, "message": "No pending technique for this action."}

        info = self._pending_techniques.pop(action_id)
        actor_id = info["actor_id"]
        target_id = info["target_id"]
        technique_id = info["technique_id"]
        actor_data = info["actor_data"]
        target_data = info["target_data"]
        equipment_engine = info["equipment_engine"]

        # Resolve through action resolution
        result = self._resolve_technique(
            actor_id=actor_id,
            target_id=target_id,
            technique_id=technique_id,
            actor_data=actor_data,
            target_data=target_data,
            equipment_engine=equipment_engine,
            current_tick=current_tick,
        )

        # Record cooldown after completion
        self._cooldowns.use_technique(actor_id, technique_id, current_tick)

        return result

    def _resolve_technique(
        self,
        actor_id: str,
        target_id: str,
        technique_id: str,
        actor_data: Dict,
        target_data: Dict,
        equipment_engine=None,
        current_tick: int = 0,
    ) -> Dict[str, Any]:
        """Resolve a technique."""
        tech_def = TECHNIQUE_DEFINITIONS[technique_id]

        # Check arcane focus requirement
        if tech_def.get("requires_arcane_focus", False):
            if not self._has_arcane_focus(actor_data, equipment_engine):
                return {
                    "success": False,
                    "hit": False,
                    "technique": technique_id,
                    "message": f"{actor_id} needs a staff or wand to use {tech_def['name']}!",
                }

        # Check and consume runestones
        runestone_cost = tech_def.get("runestone_cost", 0)
        if runestone_cost > 0:
            if not self._consume_runestones(actor_id, actor_data, runestone_cost):
                return {
                    "success": False,
                    "hit": False,
                    "technique": technique_id,
                    "message": f"{actor_id} needs {runestone_cost} runestone(s) to cast {tech_def['name']}!",
                }

        # Resolve through action resolution
        from engine.action_resolution import resolve_opposed_action, OUTCOME_SUCCESS, OUTCOME_EXCEPTIONAL_SUCCESS

        result = resolve_opposed_action(
            actor=actor_data,
            target=target_data,
            actor_attribute_name=tech_def["actor_attribute"],
            target_attribute_name=tech_def["target_attribute"],
        )

        hit = result["outcome"] in (OUTCOME_SUCCESS, OUTCOME_EXCEPTIONAL_SUCCESS)

        if not hit:
            # Build message with display names
            actor_name = actor_data.get('name', actor_id) if actor_data else actor_id
            target_name = target_data.get('name', target_id) if target_data else target_id
            
            return {
                "success": True,
                "hit": False,
                "technique": technique_id,
                "message": f"{actor_name} uses {tech_def['name']} but fails!",
                "resolution": result,
            }

        # Apply technique effects
        effects_applied = []
        if "effect" in tech_def:
            effect_def = tech_def["effect"]
            
            # Howl special: buff self and allies
            if technique_id == TECHNIQUE_HOWL and tech_def.get("buff_self"):
                # Calculate buff amount from willpower
                willpower = actor_data.get('attributes', {}).get('willpower', 50)
                buff_amount = max(1, int(willpower / 10))
                
                # Buff self
                effect = self._effects.add_effect(
                    effect_id=effect_def["effect_id"],
                    source_actor=actor_id,
                    target_actor=actor_id,
                    duration=effect_def["duration"],
                    duration_type=effect_def["duration_type"],
                    current_tick=current_tick,
                    data={"buff_stat": tech_def.get("buff_stat", "strength"), "buff_amount": buff_amount},
                )
                if effect:
                    effects_applied.append(effect)
                
                # Buff allies (same species/race, neutral or better attitude)
                if tech_def.get("buff_allies"):
                    self._buff_allies(actor_id, actor_data, effect_def, current_tick, buff_amount, tech_def)
            else:
                # Normal effect application
                effect = self._effects.add_effect(
                    effect_id=effect_def["effect_id"],
                    source_actor=actor_id,
                    target_actor=target_id,
                    duration=effect_def["duration"],
                    duration_type=effect_def["duration_type"],
                    current_tick=current_tick,
                )
                if effect:
                    effects_applied.append(effect)

        # Calculate damage if applicable
        damage = 0
        if technique_id == TECHNIQUE_BACKSTAB:
            # Check if target is not engaged with attacker
            engagement = self._combat.get_engagement()
            if not engagement.has_link(target_id, actor_id):
                # Bonus damage
                base_damage = random.randint(5, 15)
                damage = int(base_damage * tech_def.get("bonus_damage", 1.0))
                self._combat.apply_damage(target_id, damage)
            else:
                base_damage = random.randint(5, 15)
                damage = base_damage
                self._combat.apply_damage(target_id, damage)
        elif "base_damage" in tech_def:
            # Handle techniques with base_damage range (bite, claw, bow shot, etc.)
            dmg_range = tech_def["base_damage"]
            base_damage = random.randint(dmg_range["min"], dmg_range["max"])
            damage = base_damage
            self._combat.apply_damage(target_id, damage)
            
            # Double strike: attack twice
            if tech_def.get("double_strike", False):
                second_strike = random.randint(dmg_range["min"], dmg_range["max"])
                self._combat.apply_damage(target_id, second_strike)
                damage += second_strike
        
        # Add taunt if technique has taunt_amount
        if "taunt_amount" in tech_def:
            taunt_amount = tech_def["taunt_amount"]
            self._combat.add_taunt(target_id, actor_id, taunt_amount)

        # Apply arcane power multiplier from staff
        if damage > 0 and tech_def.get("requires_arcane_focus", False):
            arcane_power = self._get_arcane_power(actor_data, equipment_engine)
            if arcane_power > 1.0:
                bonus_damage = int(damage * (arcane_power - 1.0))
                self._combat.apply_damage(target_id, bonus_damage)
                damage += bonus_damage

        # Apply armor penetration for Reality Tear
        if technique_id == TECHNIQUE_REALITY_TEAR and "armor_penetration" in tech_def:
            # Armor penetration is handled in combat engine
            # For now, just note it in the message
            pass

        # Build message with display names
        actor_name = actor_data.get('name', actor_id) if actor_data else actor_id
        target_name = target_data.get('name', target_id) if target_data else target_id
        
        msg = f"{actor_name} uses {tech_def['name']} on {target_name}!"
        if effects_applied:
            msg += f" Effect applied: {effects_applied[0].get('id', 'unknown')}"
        if damage > 0:
            msg += f" {damage} damage!"
        if runestone_cost > 0:
            msg += f" (Consumed {runestone_cost} runestone(s))"

        return {
            "success": True,
            "hit": True,
            "technique": technique_id,
            "message": msg,
            "damage": damage,
            "effects": effects_applied,
            "resolution": result,
        }

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
        """Generate a combat technique event."""
        event = {
            "event_type": event_type,
            "actor_id": actor_id,
            "target_id": target_id,
            "tick": tick,
            "timestamp": time.time(),
            "data": data or {},
        }
        self._events.append(event)

    def _buff_allies(self, actor_id: str, actor_data: Dict, effect_def: Dict, current_tick: int, buff_amount: int, tech_def: Dict):
        """Buff allies of same type within range."""
        # This is called from _resolve_technique but needs access to actor positions and world data
        # The actual ally buffing is handled by CreatureAI._call_for_help setting combat targets
        # For now, the self-buff is the primary effect; ally buffing would need spatial queries
        pass

    def _has_arcane_focus(self, actor_data: Dict, equipment_engine=None) -> bool:
        """Check if actor has an arcane focus (staff or wand) equipped."""
        # Check if actor has equipped weapon that is a staff or wand
        equipment = actor_data.get('equipment', {})
        equipped_weapon = equipment.get('weapon')
        
        if not equipped_weapon:
            return False
        
        # Check weapon subtype
        weapon_id = equipped_weapon.get('id', '')
        weapon_subtype = equipped_weapon.get('subtype', '')
        
        # Check if it's a staff or wand
        if weapon_subtype in ['staff', 'wand']:
            return True
        
        # Also check item definition for arcane_focus flag
        from engine.items import get_item_definition
        item_def = get_item_definition(weapon_id)
        if item_def and item_def.get('arcane_focus', False):
            return True
        
        return False

    def _get_arcane_power(self, actor_data: Dict, equipment_engine=None) -> float:
        """Get arcane power multiplier from equipped staff."""
        equipment = actor_data.get('equipment', {})
        equipped_weapon = equipment.get('weapon')
        
        if not equipped_weapon:
            return 1.0
        
        weapon_id = equipped_weapon.get('id', '')
        
        # Check item definition for arcane_power
        from engine.items import get_item_definition
        item_def = get_item_definition(weapon_id)
        if item_def:
            return item_def.get('arcane_power', 1.0)
        
        return 1.0

    def _get_cooldown_reduction(self, actor_data: Dict, equipment_engine=None) -> float:
        """Get cooldown reduction from equipped wand."""
        equipment = actor_data.get('equipment', {})
        equipped_weapon = equipment.get('weapon')
        
        if not equipped_weapon:
            return 0.0
        
        weapon_id = equipped_weapon.get('id', '')
        
        # Check item definition for cooldown_reduction
        from engine.items import get_item_definition
        item_def = get_item_definition(weapon_id)
        if item_def:
            return item_def.get('cooldown_reduction', 0.0)
        
        return 0.0

    def _consume_runestones(self, actor_id: str, actor_data: Dict, amount: int) -> bool:
        """Consume runestones from actor's inventory."""
        # This would integrate with the inventory system
        # For now, return True (assume player has runestones)
        # TODO: Integrate with actual inventory system
        return True
