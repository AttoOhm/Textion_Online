"""
Whirlwind Command (Sword Technique)

Real command: whirlwind

A spinning attack that hits all nearby enemies and stuns them.
Requires sword equipped. AoE node attack.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.long_action import ActionQueue, process_tick, STATUS_COMPLETED
from engine.action_resolution import resolve_action, ACTION_TYPE_OPPOSED


def handle_whirlwind(player_state, target_id, world_map, current_tick, action_queue, technique_manager=None, equipment_engine=None, combat_engine=None):
    """Handle the 'whirlwind' command."""
    # Check technique ownership
    if technique_manager:
        if not technique_manager.has_technique(player_state.get("id", "player"), "whirlwind"):
            return {
                "success": False,
                "message": "You do not know the Whirlwind technique.",
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
                "message": "You need a sword equipped to use Whirlwind.",
                "events": []
            }
        from engine.items import get_item_definition
        item_def = get_item_definition(equipped.get("item_id", ""))
        if not item_def or item_def.get("subtype") != "sword":
            return {
                "success": False,
                "message": "You need a sword equipped to use Whirlwind.",
                "events": []
            }

    # Create Long Action for whirlwind (2 ticks)
    action = action_queue.queue_action(
        actor_id=player_state.get("id", "player"),
        action_type="whirlwind",
        duration_ticks=2,
        current_tick=current_tick,
        target=None,  # AoE - no specific target
        parameters={
            "target_id": "all_nearby",
        },
        resolution_config={
            "action_type": ACTION_TYPE_OPPOSED,
            "attribute_name": "strength",
            "target_attribute_name": "constitution",
            "technique_name": "whirlwind",
        }
    )

    if not action:
        return {
            "success": False,
            "message": "Failed to start Whirlwind.",
            "events": []
        }

    return {
        "success": True,
        "message": "You begin a spinning attack, preparing to strike all nearby enemies...",
        "action_id": action["action_id"],
        "events": action_queue.get_events()
    }


def resolve_whirlwind(action, player_state, world_map, current_tick, combat_engine, technique_engine=None, actor_positions=None, get_actors_at_position_func=None):
    """Resolve a completed whirlwind action."""
    player_id = player_state.get("id", "player")
    player_pos = actor_positions.get(player_id) if actor_positions else None
    
    if not player_pos:
        return {
            "outcome": "failure",
            "message": "You cannot determine your position for Whirlwind!",
        }
    
    # Get all actors at player's position
    targets = []
    if get_actors_at_position_func:
        actors_here = get_actors_at_position_func(player_pos.get('map_id'), player_pos.get('node_id'))
        for actor_id in actors_here:
            if actor_id != player_id:
                targets.append(actor_id)
    
    if not targets:
        return {
            "outcome": "success",
            "message": "You spin around but there are no enemies nearby!",
        }
    
    # Run action resolution
    resolution = resolve_action(
        action_type=ACTION_TYPE_OPPOSED,
        actor=player_state,
        attribute_name="strength",
        target=player_state,  # Self vs self for base resolution
        target_attribute_name="constitution",
        technique_name="whirlwind",
    )
    
    outcome = resolution["outcome"]
    
    if outcome in ("success", "exceptional_success", "partial_success"):
        # Hit all nearby targets
        base_damage = 9  # Average of 6-12
        hit_targets = []
        
        for target_id in targets:
            # Get target data
            target_data = find_target(target_id, world_map)
            if not target_data:
                continue
            
            # Attack each target
            result = combat_engine.attack(
                attacker_id=player_id,
                target_id=target_id,
                current_tick=current_tick,
                attacker_data=player_state,
                target_data=target_data,
                weapon_damage=base_damage,
                attack_profile={
                    "id": "whirlwind",
                    "name": "Whirlwind",
                    "damage_type": "slashing",
                    "base_damage": base_damage,
                    "constructed_attribute": {"strength": 1.0},
                    "apply_attribute_damage_bonus": True,
                    "is_melee": True,
                    "is_ranged": False,
                    "targeting_mode": "melee",
                    "target_scope": "single_actor",
                }
            )
            
            # Apply stun effect
            if hasattr(combat_engine, '_effects') and combat_engine._effects:
                combat_engine._effects.add_effect(
                    effect_id="stunned",
                    source_actor=player_id,
                    target_actor=target_id,
                    duration=1,
                    duration_type="timed",
                    current_tick=current_tick,
                )
            
            hit_targets.append(target_id)
        
        message = f"Whirlwind hits {len(hit_targets)} target(s): {', '.join(hit_targets)}! All stunned!"
        
        return {
            "outcome": outcome,
            "message": message,
            "resolution": resolution,
            "targets_hit": hit_targets,
        }
    else:
        return {
            "outcome": outcome,
            "message": "Your Whirlwind misses all targets!",
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