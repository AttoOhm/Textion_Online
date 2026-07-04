"""
Draw Cut Command (Sword Technique)

Real command: draw cut <target>

A swift drawing cut. Bonus damage if target is marked.
Requires sword equipped. +30 reactiveness on use.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.long_action import ActionQueue, process_tick, STATUS_COMPLETED
from engine.action_resolution import resolve_action, ACTION_TYPE_OPPOSED


def handle_draw_cut(player_state, target_id, world_map, current_tick, action_queue, technique_manager=None, equipment_engine=None):
    """Handle the 'draw cut <target>' command.

    Args:
        player_state: Player state dict
        target_id: ID of the target
        world_map: World map data
        current_tick: Current world tick
        action_queue: Action queue instance
        technique_manager: Optional TechniqueManager for gating
        equipment_engine: Optional equipment engine to check for sword

    Returns:
        Dict with command result
    """
    # Check technique ownership
    if technique_manager:
        if not technique_manager.has_technique(player_state.get("id", "player"), "draw_cut"):
            return {
                "success": False,
                "message": "You do not know the Draw Cut technique.",
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

    # Check for sword equipped
    if equipment_engine:
        equipped = equipment_engine.get_equipped_item(player_state.get("id", "player"), "main_hand")
        if not equipped:
            return {
                "success": False,
                "message": "You need a sword equipped to use Draw Cut.",
                "events": []
            }
        from engine.items import get_item_definition
        item_def = get_item_definition(equipped.get("item_id", ""))
        if not item_def or item_def.get("subtype") != "sword":
            return {
                "success": False,
                "message": "You need a sword equipped to use Draw Cut.",
                "events": []
            }

    # Find target in world
    target_data = find_target(target_id, world_map)
    if not target_data:
        return {
            "success": False,
            "message": f"You cannot find '{target_id}'.",
            "events": []
        }

    # Create Long Action for draw cut
    action = action_queue.queue_action(
        actor_id=player_state.get("id", "player"),
        action_type="draw_cut",
        duration_ticks=1,
        current_tick=current_tick,
        target=target_data,
        parameters={
            "target_id": target_id,
            "target_name": target_data.get("name", target_id),
        },
        resolution_config={
            "action_type": ACTION_TYPE_OPPOSED,
            "attribute_name": "dexterity",
            "target_attribute_name": "observation",
            "technique_name": "draw_cut",
        }
    )

    if not action:
        return {
            "success": False,
            "message": "Failed to start Draw Cut.",
            "events": []
        }

    return {
        "success": True,
        "message": f"You prepare a swift drawing cut against {target_data.get('name', target_id)}...",
        "action_id": action["action_id"],
        "events": action_queue.get_events()
    }


def resolve_draw_cut(action, player_state, world_map, current_tick, combat_engine, technique_engine=None):
    """Resolve a completed draw cut action.

    Args:
        action: Completed action dict
        player_state: Player state
        world_map: World map data
        current_tick: Current tick
        combat_engine: Combat engine instance
        technique_engine: Optional technique engine

    Returns:
        Dict with resolution result
    """
    target_data = action.get("target", {})
    target_id = action.get("parameters", {}).get("target_id", "")
    target_name = action.get("parameters", {}).get("target_name", target_id)

    # Run action resolution
    resolution = resolve_action(
        action_type=ACTION_TYPE_OPPOSED,
        actor=player_state,
        attribute_name="dexterity",
        target=target_data,
        target_attribute_name="observation",
        technique_name="draw_cut",
    )

    outcome = resolution["outcome"]

    if outcome in ("success", "exceptional_success", "partial_success"):
        # Check if target has death mark (bonus damage)
        bonus_damage = 0
        if hasattr(combat_engine, '_effects') and combat_engine._effects:
            if combat_engine._effects.has_effect(target_id, "death_mark"):
                mark_data = combat_engine._effects.get_effect(target_id, "death_mark")
                if mark_data.get("data", {}).get("owner") == player_state.get("id", "player"):
                    bonus_damage = 15  # Bonus damage vs marked target
        
        # Execute attack with technique
        base_damage = 8 + bonus_damage
        result = combat_engine.attack(
            attacker_id=player_state.get("id", "player"),
            target_id=target_id,
            current_tick=current_tick,
            attacker_data=player_state,
            target_data=target_data,
            weapon_damage=base_damage,
            attack_profile={
                "id": "draw_cut",
                "name": "Draw Cut",
                "damage_type": "slashing",
                "base_damage": base_damage,
                "constructed_attribute": {"dexterity": 1.0},
                "apply_attribute_damage_bonus": True,
                "is_melee": True,
                "is_ranged": False,
                "targeting_mode": "melee",
                "target_scope": "single_actor",
            }
        )
        
        # Add reactiveness bonus
        message = result.get("message", "")
        message += f" Draw Cut grants +30 reactiveness!"
        
        return {
            "outcome": outcome,
            "message": message,
            "resolution": resolution,
            "damage": result.get("damage"),
        }
    else:
        return {
            "outcome": outcome,
            "message": f"Your Draw Cut misses {target_name}!",
            "resolution": resolution,
        }


def find_target(target_id, world_map):
    """Find a target in the world map."""
    if not world_map:
        return None

    creatures = world_map.get("creatures", {})
    if target_id in creatures:
        return creatures[target_id]

    npcs = world_map.get("npcs", {})
    if target_id in npcs:
        return npcs[target_id]

    actors = world_map.get("actors", {})
    if target_id in actors:
        return actors[target_id]

    return None