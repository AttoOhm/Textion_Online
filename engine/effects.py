"""
Effect System (Phase 5A)

Implements the generic Effect System designed in Phase 4E.
This is the first gameplay-support implementation phase.

Key Properties:
- Effects modify the world temporarily
- Effects have a duration and lifecycle
- Effects generate events on apply/remove/expire
- Effects may contain modifiers (storage only, not applied yet)

Statuses:
- instant: Applied and removed immediately
- timed: Lasts for a specific number of ticks
- permanent: Lasts until removed
- conditional: Lasts while condition is true
"""

import uuid
import time
from typing import Optional, Dict, List, Any

# ============ CONSTANTS ============

DURATION_INSTANT = "instant"
DURATION_TIMED = "timed"
DURATION_PERMANENT = "permanent"
DURATION_CONDITIONAL = "conditional"

VALID_DURATION_TYPES = [
    DURATION_INSTANT,
    DURATION_TIMED,
    DURATION_PERMANENT,
    DURATION_CONDITIONAL,
]

# Event types
EVENT_EFFECT_APPLIED = "effect_applied"
EVENT_EFFECT_REMOVED = "effect_removed"
EVENT_EFFECT_EXPIRED = "effect_expired"

# ============ EFFECT SCHEMA ============


def create_effect(
    effect_id: str,
    source_actor: str = "",
    target_actor: str = "",
    duration: int = 1,
    duration_type: str = DURATION_TIMED,
    created_tick: int = 0,
    data: Optional[Dict] = None,
    attribute_modifiers: Optional[Dict] = None,
    resolution_modifiers: Optional[Dict] = None,
    visibility_modifiers: Optional[Dict] = None,
    reputation_modifiers: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Create a canonical Effect structure.

    Args:
        effect_id: Unique effect identifier
        source_actor: Actor that created the effect
        target_actor: Actor the effect is applied to
        duration: Duration in ticks (for timed effects)
        duration_type: Type of duration (instant, timed, permanent, conditional)
        created_tick: Tick when effect was created
        data: Optional effect-specific data
        attribute_modifiers: Optional attribute modifiers
        resolution_modifiers: Optional resolution modifiers
        visibility_modifiers: Optional visibility modifiers
        reputation_modifiers: Optional reputation modifiers

    Returns:
        Dict representing the effect
    """
    return {
        "id": effect_id,
        "source_actor": source_actor,
        "target_actor": target_actor,
        "duration": duration,
        "duration_type": duration_type,
        "created_tick": created_tick,
        "remaining_ticks": duration,
        "data": data or {},
        "modifiers": {
            "attribute_modifiers": attribute_modifiers or {},
            "resolution_modifiers": resolution_modifiers or {},
            "visibility_modifiers": visibility_modifiers or {},
            "reputation_modifiers": reputation_modifiers or {},
        },
    }


def validate_effect(effect: Dict[str, Any]) -> List[str]:
    """Validate an effect structure. Returns list of errors (empty = valid)."""
    errors = []
    required = ["id", "source_actor", "target_actor", "duration_type"]
    for field in required:
        if field not in effect:
            errors.append(f"Missing required field: {field}")
    if effect.get("duration_type") not in VALID_DURATION_TYPES:
        errors.append(f"Invalid duration_type: {effect.get('duration_type')}")
    return errors


# ============ EFFECT ENGINE ============


class EffectEngine:
    """Runtime effect storage and management.

    Manages active effects for all actors.
    """

    def __init__(self):
        self._effects: Dict[str, Dict[str, Any]] = {}  # effect_key -> effect
        self._actor_effects: Dict[str, List[str]] = {}  # actor_id -> [effect_keys]
        self._events: List[Dict[str, Any]] = []

    def add_effect(
        self,
        effect_id: str,
        source_actor: str,
        target_actor: str,
        duration: int = 1,
        duration_type: str = DURATION_TIMED,
        current_tick: int = 0,
        data: Optional[Dict] = None,
        attribute_modifiers: Optional[Dict] = None,
        resolution_modifiers: Optional[Dict] = None,
        visibility_modifiers: Optional[Dict] = None,
        reputation_modifiers: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """Add an effect to a target actor.

        Args:
            effect_id: Effect identifier
            source_actor: Actor that created the effect
            target_actor: Actor the effect is applied to
            duration: Duration in ticks
            duration_type: Type of duration
            current_tick: Current world tick
            data: Optional effect-specific data
            attribute_modifiers: Optional attribute modifiers
            resolution_modifiers: Optional resolution modifiers
            visibility_modifiers: Optional visibility modifiers
            reputation_modifiers: Optional reputation modifiers

        Returns:
            The created effect dict, or None if invalid
        """
        # Create the effect
        effect = create_effect(
            effect_id=effect_id,
            source_actor=source_actor,
            target_actor=target_actor,
            duration=duration,
            duration_type=duration_type,
            created_tick=current_tick,
            data=data,
            attribute_modifiers=attribute_modifiers,
            resolution_modifiers=resolution_modifiers,
            visibility_modifiers=visibility_modifiers,
            reputation_modifiers=reputation_modifiers,
        )

        # Validate
        errors = validate_effect(effect)
        if errors:
            return None

        # Generate unique key
        effect_key = f"{target_actor}_{effect_id}_{current_tick}"
        effect["_key"] = effect_key

        # Store the effect
        self._effects[effect_key] = effect

        # Track by actor
        if target_actor not in self._actor_effects:
            self._actor_effects[target_actor] = []
        self._actor_effects[target_actor].append(effect_key)

        # Generate event
        self._generate_event(EVENT_EFFECT_APPLIED, effect, current_tick)

        # Handle instant effects
        if duration_type == DURATION_INSTANT:
            self.remove_effect(effect_key, current_tick)

        return effect

    def remove_effect(self, effect_key: str, current_tick: int = 0) -> bool:
        """Remove an effect.

        Args:
            effect_key: The effect key to remove
            current_tick: Current world tick

        Returns:
            True if removed, False if not found
        """
        effect = self._effects.get(effect_key)
        if not effect:
            return False

        # Remove from storage
        del self._effects[effect_key]

        # Remove from actor tracking
        target_actor = effect["target_actor"]
        if target_actor in self._actor_effects:
            if effect_key in self._actor_effects[target_actor]:
                self._actor_effects[target_actor].remove(effect_key)

        # Generate event
        self._generate_event(EVENT_EFFECT_REMOVED, effect, current_tick)

        return True

    def has_effect(self, actor_id: str, effect_id: str) -> bool:
        """Check if an actor has a specific effect.

        Args:
            actor_id: Actor identifier
            effect_id: Effect identifier

        Returns:
            True if actor has the effect
        """
        actor_keys = self._actor_effects.get(actor_id, [])
        for key in actor_keys:
            effect = self._effects.get(key)
            if effect and effect["id"] == effect_id:
                return True
        return False

    def get_effect(self, actor_id: str, effect_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific effect for an actor.

        Args:
            actor_id: Actor identifier
            effect_id: Effect identifier

        Returns:
            Effect dict or None
        """
        actor_keys = self._actor_effects.get(actor_id, [])
        for key in actor_keys:
            effect = self._effects.get(key)
            if effect and effect["id"] == effect_id:
                return effect
        return None

    def get_effects(self, actor_id: str) -> List[Dict[str, Any]]:
        """Get all effects for an actor.

        Args:
            actor_id: Actor identifier

        Returns:
            List of effect dicts
        """
        actor_keys = self._actor_effects.get(actor_id, [])
        effects = []
        for key in actor_keys:
            effect = self._effects.get(key)
            if effect:
                effects.append(effect)
        return effects

    def get_all_effects(self) -> List[Dict[str, Any]]:
        """Get all active effects.

        Returns:
            List of all effect dicts
        """
        return list(self._effects.values())

    def update_effects(self, current_tick: int) -> List[Dict[str, Any]]:
        """Update all effects for a tick.

        Args:
            current_tick: Current world tick

        Returns:
            List of expired effects
        """
        expired = []

        for effect_key, effect in list(self._effects.items()):
            if effect["duration_type"] == DURATION_TIMED:
                # Reduce remaining ticks
                effect["remaining_ticks"] -= 1

                # Check if expired
                if effect["remaining_ticks"] <= 0:
                    expired.append(effect)
                    # Generate expiration event
                    self._generate_event(EVENT_EFFECT_EXPIRED, effect, current_tick)
                    # Remove the effect
                    self.remove_effect(effect_key, current_tick)

        return expired

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all generated events.

        Returns:
            List of event dicts
        """
        return list(self._events)

    def clear_events(self):
        """Clear all events."""
        self._events.clear()

    def _generate_event(self, event_type: str, effect: Dict[str, Any], tick: int):
        """Generate an event for an effect lifecycle change."""
        event = {
            "event_type": event_type,
            "effect_id": effect["id"],
            "source_actor": effect["source_actor"],
            "target_actor": effect["target_actor"],
            "duration_type": effect["duration_type"],
            "tick": tick,
            "timestamp": time.time(),
            "data": {
                "duration": effect.get("duration", 0),
                "remaining_ticks": effect.get("remaining_ticks", 0),
            },
        }
        self._events.append(event)


# ============ TEST EFFECTS ============


def create_test_effects():
    """Create validation test effects. No gameplay implementation."""
    return {
        "rested": create_effect(
            effect_id="rested",
            source_actor="system",
            target_actor="player",
            duration=5,
            duration_type=DURATION_TIMED,
            data={"description": "Well rested"},
        ),
        "inspired": create_effect(
            effect_id="inspired",
            source_actor="system",
            target_actor="player",
            duration=3,
            duration_type=DURATION_TIMED,
            data={"description": "Feeling inspired"},
        ),
        "observed": create_effect(
            effect_id="observed",
            source_actor="system",
            target_actor="player",
            duration=1,
            duration_type=DURATION_TIMED,
            data={"description": "Being observed"},
        ),
        "exhausted": create_effect(
            effect_id="exhausted",
            source_actor="system",
            target_actor="player",
            duration=10,
            duration_type=DURATION_TIMED,
            data={"description": "Exhausted from effort"},
        ),
    }


# ============ DEMO ============


def run_demo():
    """Demonstrate the effect system."""
    print("=" * 60)
    print("EFFECT SYSTEM - DEMO")
    print("=" * 60)

    engine = EffectEngine()

    # Apply effect
    print("\n--- Tick 0: Apply 'rested' effect ---")
    effect = engine.add_effect(
        effect_id="rested",
        source_actor="system",
        target_actor="player",
        duration=3,
        duration_type=DURATION_TIMED,
        current_tick=0,
    )
    print(f"Effect: {effect['id']}")
    print(f"Remaining: {effect['remaining_ticks']}")

    # Check effect exists
    print("\n--- Check effect exists ---")
    has = engine.has_effect("player", "rested")
    print(f"Has 'rested': {has}")

    # Get effects
    print("\n--- Get all effects for player ---")
    effects = engine.get_effects("player")
    print(f"Effects count: {len(effects)}")

    # Tick 1
    print("\n--- Tick 1 ---")
    expired = engine.update_effects(1)
    effects = engine.get_effects("player")
    if effects:
        print(f"Remaining: {effects[0]['remaining_ticks']}")

    # Tick 2
    print("\n--- Tick 2 ---")
    expired = engine.update_effects(2)
    effects = engine.get_effects("player")
    if effects:
        print(f"Remaining: {effects[0]['remaining_ticks']}")

    # Tick 3 (expires)
    print("\n--- Tick 3 ---")
    expired = engine.update_effects(3)
    print(f"Expired: {len(expired)}")
    effects = engine.get_effects("player")
    print(f"Effects remaining: {len(effects)}")

    # Check events
    print("\n--- Events ---")
    events = engine.get_events()
    for event in events:
        print(f"  {event['event_type']}: {event['effect_id']}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()