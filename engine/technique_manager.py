"""
Technique Manager (Phase 5C)

Implements the Technique Framework designed in Phase 3 and Phase 4.
Techniques are now real gameplay objects.

Key Properties:
- Learn and forget techniques
- Capacity validation
- Prerequisite validation
- Cooldown storage
- Event generation

No combat. No magic. No crafting. No inventory.
No technique effects. No technique content.
"""

import time
from typing import Optional, Dict, List, Any, Tuple

# ============ CONSTANTS ============

# Capacity model (frozen)
TECHNIQUE_CAPACITY = {
    "minor": 8,
    "major": 6,
    "master": 4,
    "legendary": 2,
}

# Valid tiers
VALID_TIERS = ["minor", "major", "master", "legendary"]

# Event types
EVENT_TECHNIQUE_LEARNED = "technique_learned"
EVENT_TECHNIQUE_FORGOTTEN = "technique_forgotten"

# ============ TECHNIQUE SCHEMA ============


def create_technique(
    technique_id: str,
    name: str = "",
    discipline: str = "",
    lvl: int = 1,
    tier: str = "minor",
    category: str = "active",
    description: str = "",
    cooldown_remaining: int = 0,
    prerequisites: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Create a canonical Technique structure.

    Args:
        technique_id: Unique technique identifier
        name: Display name
        discipline: Parent discipline
        lvl: Technique level (1-5)
        tier: Technique tier (minor, major, master, legendary)
        category: Technique category
        description: Human-readable description
        cooldown_remaining: Cooldown ticks remaining
        prerequisites: Prerequisite requirements

    Returns:
        Dict representing the technique
    """
    return {
        "id": technique_id,
        "name": name or technique_id,
        "discipline": discipline,
        "lvl": max(1, min(5, lvl)),
        "tier": tier if tier in VALID_TIERS else "minor",
        "category": category,
        "description": description,
        "cooldown_remaining": cooldown_remaining,
        "prerequisites": prerequisites or {},
    }


def validate_technique(technique: Dict[str, Any]) -> List[str]:
    """Validate a technique structure. Returns list of errors (empty = valid)."""
    errors = []
    required = ["id", "name", "discipline", "lvl", "category"]
    for field in required:
        if field not in technique:
            errors.append(f"Missing required field: {field}")
    if technique.get("lvl") not in range(1, 6):
        errors.append(f"Invalid lvl: {technique.get('lvl')}")
    return errors


# ============ TECHNIQUE MANAGER ============


class TechniqueManager:
    """Runtime technique storage and management.

    Manages techniques for all actors.
    """

    def __init__(self):
        self._techniques: Dict[str, Dict[str, Any]] = {}  # technique_id -> technique
        self._actor_techniques: Dict[str, Dict[str, Any]] = {}  # actor_id -> {technique_id: technique}
        self._events: List[Dict[str, Any]] = []

    def learn_technique(
        self,
        actor_id: str,
        technique_id: str,
        name: str = "",
        discipline: str = "",
        lvl: int = 1,
        tier: str = "minor",
        category: str = "active",
        description: str = "",
        current_tick: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """Learn a technique.

        Args:
            actor_id: Actor identifier
            technique_id: Technique identifier
            name: Display name
            discipline: Parent discipline
            lvl: Technique level (1-5)
            tier: Technique tier (minor, major, master, legendary)
            category: Technique category
            description: Human-readable description
            current_tick: Current world tick

        Returns:
            The learned technique dict, or None if failed
        """
        # Check if already learned
        if self.has_technique(actor_id, technique_id):
            return None

        # Create technique
        technique = create_technique(
            technique_id=technique_id,
            name=name,
            discipline=discipline,
            lvl=lvl,
            tier=tier,
            category=category,
            description=description,
        )

        # Validate
        errors = validate_technique(technique)
        if errors:
            return None

        # Check capacity
        if not self._check_capacity(actor_id, technique):
            return None

        # Check prerequisites
        if not self._check_prerequisites(actor_id, technique):
            return None

        # Store technique
        if actor_id not in self._actor_techniques:
            self._actor_techniques[actor_id] = {}
        self._actor_techniques[actor_id][technique_id] = technique

        # Generate event
        self._generate_event(EVENT_TECHNIQUE_LEARNED, actor_id, technique_id, current_tick)

        return technique

    def forget_technique(
        self,
        actor_id: str,
        technique_id: str,
        current_tick: int = 0,
    ) -> bool:
        """Forget a technique.

        Args:
            actor_id: Actor identifier
            technique_id: Technique identifier
            current_tick: Current world tick

        Returns:
            True if forgotten, False if not found
        """
        if not self.has_technique(actor_id, technique_id):
            return False

        # Remove technique
        del self._actor_techniques[actor_id][technique_id]

        # Generate event
        self._generate_event(EVENT_TECHNIQUE_FORGOTTEN, actor_id, technique_id, current_tick)

        return True

    def has_technique(self, actor_id: str, technique_id: str) -> bool:
        """Check if an actor has a technique.

        Args:
            actor_id: Actor identifier
            technique_id: Technique identifier

        Returns:
            True if actor has the technique
        """
        actor_techniques = self._actor_techniques.get(actor_id, {})
        return technique_id in actor_techniques

    def get_technique(self, actor_id: str, technique_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific technique for an actor.

        Args:
            actor_id: Actor identifier
            technique_id: Technique identifier

        Returns:
            Technique dict or None
        """
        actor_techniques = self._actor_techniques.get(actor_id, {})
        return actor_techniques.get(technique_id)

    def get_techniques(self, actor_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all techniques for an actor.

        Args:
            actor_id: Actor identifier

        Returns:
            Dict of technique_id -> technique
        """
        return dict(self._actor_techniques.get(actor_id, {}))

    def can_learn_technique(
        self,
        actor_id: str,
        technique_id: str,
        discipline: str = "",
        lvl: int = 1,
        tier: str = "minor",
    ) -> Tuple[bool, str]:
        """Check if an actor can learn a technique.

        Args:
            actor_id: Actor identifier
            technique_id: Technique identifier
            discipline: Parent discipline
            lvl: Technique level
            tier: Technique tier

        Returns:
            Tuple of (can_learn, reason)
        """
        # Check if already learned
        if self.has_technique(actor_id, technique_id):
            return False, "Already learned"

        # Check capacity
        technique = create_technique(
            technique_id=technique_id,
            discipline=discipline,
            lvl=lvl,
            tier=tier,
        )
        if not self._check_capacity(actor_id, technique):
            return False, "Capacity exceeded"

        # Check prerequisites
        if not self._check_prerequisites(actor_id, technique):
            return False, "Prerequisites not met"

        return True, "Can learn"

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all generated events.

        Returns:
            List of event dicts
        """
        return list(self._events)

    def clear_events(self):
        """Clear all events."""
        self._events.clear()

    def _check_capacity(self, actor_id: str, technique: Dict[str, Any]) -> bool:
        """Check if actor has capacity for a technique.

        Args:
            actor_id: Actor identifier
            technique: Technique to check

        Returns:
            True if capacity available
        """
        actor_techniques = self._actor_techniques.get(actor_id, {})
        tier = technique.get("tier", "minor")
        max_slots = TECHNIQUE_CAPACITY.get(tier, 0)

        # Count techniques in this tier
        count = 0
        for tech in actor_techniques.values():
            if tech.get("tier", "minor") == tier:
                count += 1

        return count < max_slots

    def _check_prerequisites(self, actor_id: str, technique: Dict[str, Any]) -> bool:
        """Check if actor meets prerequisites for a technique.

        Args:
            actor_id: Actor identifier
            technique: Technique to check

        Returns:
            True if prerequisites met
        """
        prerequisites = technique.get("prerequisites", {})

        # Check required techniques
        required_techniques = prerequisites.get("techniques", [])
        for req_tech in required_techniques:
            if not self.has_technique(actor_id, req_tech):
                return False

        # Check minimum technique level
        min_lvl = prerequisites.get("min_lvl", 0)
        if min_lvl > 0:
            for tech in self.get_techniques(actor_id).values():
                if tech.get("lvl", 0) >= min_lvl:
                    break
            else:
                return False

        # Check discipline value
        min_discipline = prerequisites.get("min_discipline", 0)
        if min_discipline > 0:
            # This would check player's discipline value
            # For now, return True (no player state integration)
            pass

        # Check reputation
        min_reputation = prerequisites.get("min_reputation", 0)
        if min_reputation > 0:
            # This would check player's reputation
            # For now, return True (no player state integration)
            pass

        # Check faction
        required_faction = prerequisites.get("faction", "")
        if required_faction:
            # This would check player's faction membership
            # For now, return True (no player state integration)
            pass

        return True


    def _generate_event(self, event_type: str, actor_id: str, technique_id: str, tick: int):
        """Generate an event for a technique lifecycle change."""
        event = {
            "event_type": event_type,
            "actor_id": actor_id,
            "technique_id": technique_id,
            "tick": tick,
            "timestamp": time.time(),
        }
        self._events.append(event)


# ============ DEMO ============


def run_demo():
    """Demonstrate the technique framework."""
    print("=" * 60)
    print("TECHNIQUE FRAMEWORK - DEMO")
    print("=" * 60)

    manager = TechniqueManager()

    # Learn Track Prey
    print("\n--- Learn Track Prey ---")
    tech = manager.learn_technique(
        actor_id="player",
        technique_id="track_prey",
        name="Track Prey",
        discipline="hunting",
        lvl=2,
        category="active",
        description="Track a creature through the wilderness",
    )
    print(f"Learned: {tech['name']} (lvl {tech['lvl']})")

    # Verify technique exists
    print("\n--- Verify technique exists ---")
    has = manager.has_technique("player", "track_prey")
    print(f"Has 'track_prey': {has}")

    # Get technique
    print("\n--- Get technique ---")
    tech = manager.get_technique("player", "track_prey")
    print(f"Technique: {tech['name']} (lvl {tech['lvl']})")

    # Get all techniques
    print("\n--- Get all techniques ---")
    techniques = manager.get_techniques("player")
    print(f"Techniques count: {len(techniques)}")

    # Forget Track Prey
    print("\n--- Forget Track Prey ---")
    forgotten = manager.forget_technique("player", "track_prey")
    print(f"Forgotten: {forgotten}")

    # Verify technique removed
    print("\n--- Verify technique removed ---")
    has = manager.has_technique("player", "track_prey")
    print(f"Has 'track_prey': {has}")

    # Check events
    print("\n--- Events ---")
    events = manager.get_events()
    for event in events:
        print(f"  {event['event_type']}: {event['technique_id']}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()