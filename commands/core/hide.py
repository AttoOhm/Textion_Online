"""
Hide Command (Phase 5C)

Real command: hide behind [world item]

Hiding allows one to not be included in the scene of actors
that don't succeed in spotting them.

This is an opposed action:
- Hider: Dexterity + Stealth
- Observer: Observation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.long_action import ActionQueue, process_tick, STATUS_COMPLETED
from engine.action_resolution import resolve_action, ACTION_TYPE_OPPOSED
from engine.effects import EffectEngine, DURATION_TIMED


def handle_hide(player_state, hide_location, world_map, current_tick, action_queue, effect_engine, technique_manager=None):
    """Handle the 'hide behind <item>' command.

    Args:
        player_state: Player state dict
        hide_location: Location to hide behind
        world_map: World map data
        current_tick: Current world tick
        action_queue: Action queue instance
        effect_engine: Effect engine instance
        technique_manager: Optional TechniqueManager for gating

    Returns:
        Dict with command result
    """
    # Check technique ownership
    if technique_manager:
        if not technique_manager.has_technique(player_state.get("id", "player"), "stealth"):
            return {
                "success": False,
                "message": "You do not know the Stealth technique.",
                "events": []
            }

    # Check if player already has an active action
    existing = action_queue.get_actor_action(player_state.get("id", "player"))
    if existing:
        return {
            "success": False,
            "message": "You are already performing an action.",
            "events": []
        }

    # Find hide location in world
    location_data = find_location(hide_location, world_map)
    if not location_data:
        return {
            "success": False,
            "message": f"You cannot find '{hide_location}' to hide behind.",
            "events": []
        }

    # Create Long Action for hiding
    action = action_queue.queue_action(
        actor_id=player_state.get("id", "player"),
        action_type="hide",
        duration_ticks=1,  # Takes 1 tick to hide
        current_tick=current_tick,
        target=location_data,
        parameters={
            "location_id": hide_location,
            "location_name": location_data.get("name", hide_location),
        },
        resolution_config={
            "action_type": ACTION_TYPE_OPPOSED,
            "attribute_name": "dexterity",
            "target_attribute_name": "observation",
            "technique_name": "stealth",
        }
    )

    if not action:
        return {
            "success": False,
            "message": "Failed to start hiding.",
            "events": []
        }

    return {
        "success": True,
        "message": f"You begin hiding behind {location_data.get('name', hide_location)}...",
        "action_id": action["action_id"],
        "events": action_queue.get_events()
    }


def resolve_hide(action, player_state, observers, world_map, current_tick, effect_engine):
    """Resolve a completed hide action.

    Args:
        action: Completed action dict
        player_state: Player state
        observers: List of observer actors
        world_map: World map data
        current_tick: Current tick
        effect_engine: Effect engine

    Returns:
        Dict with resolution result
    """
    location_data = action.get("target", {})
    hidden_from = []

    # Check against each observer
    for observer in observers:
        resolution = resolve_action(
            action_type=ACTION_TYPE_OPPOSED,
            actor=player_state,
            attribute_name="dexterity",
            target=observer,
            target_attribute_name="observation",
            technique_name="stealth",
        )

        outcome = resolution["outcome"]

        if outcome in ("failure", "critical_failure"):
            # Observer spotted the hider
            pass
        else:
            # Hider is hidden from this observer
            hidden_from.append(observer.get("name", "unknown"))

    # Apply hidden effect if hidden from anyone
    if hidden_from:
        effect_engine.add_effect(
            effect_id="hidden",
            source_actor=player_state.get("id", "player"),
            target_actor=player_state.get("id", "player"),
            duration=5,
            duration_type=DURATION_TIMED,
            current_tick=current_tick,
            data={
                "hidden_from": hidden_from,
                "location": location_data.get("name", "unknown"),
            },
        )
        message = f"You are now hidden from {', '.join(hidden_from)}."
    else:
        message = "You failed to hide from anyone."

    return {
        "outcome": "success" if hidden_from else "failure",
        "message": message,
        "hidden_from": hidden_from,
    }


def find_location(location_id, world_map):
    """Find a location in the world map."""
    if not world_map:
        return None

    # Check nodes
    nodes = world_map.get("nodes", {})
    if location_id in nodes:
        return nodes[location_id]

    # Check objects
    objects = world_map.get("objects", {})
    if location_id in objects:
        return objects[location_id]

    return None


def run_demo():
    """Demonstrate the Hide command."""
    print("=" * 60)
    print("HIDE COMMAND - DEMO")
    print("=" * 60)

    player_state = {
        "id": "player",
        "name": "Player",
        "attributes": {"dexterity": 50, "observation": 40},
        "techniques": {"stealth": {"lvl": 2}},
    }

    guard = {
        "id": "guard",
        "name": "Guard",
        "attributes": {"observation": 40},
    }

    world_map = {
        "objects": {
            "bush": {"id": "bush", "name": "Large Bush"},
        }
    }

    queue = ActionQueue()
    effects = EffectEngine()
    current_tick = 0

    print("\n--- Player issues: hide behind bush ---")
    result = handle_hide(player_state, "bush", world_map, current_tick, queue, effects)
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")

    print("\n--- Tick 1 ---")
    process_tick(queue, 1)

    action = queue.get_actor_action("player")
    if action:
        completed = queue.complete_action(action["action_id"], 1)
        if completed:
            resolution = resolve_hide(completed, player_state, [guard], world_map, 1, effects)
            print(f"Outcome: {resolution['outcome']}")
            print(f"Message: {resolution['message']}")

    print("\n--- Events ---")
    for event in queue.get_events():
        print(f"  {event['event_type']}: {event['action_type']} ({event['status']})")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()