"""
Sword Dance Command (Sword Technique)

Real command: sword dance <target>

A complex 3-step sequence. Each step requires different input.
Final step hits 3 targets and applies taunt.
Requires sword equipped.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.long_action import ActionQueue, process_tick, STATUS_COMPLETED
from engine.action_resolution import resolve_action, ACTION_TYPE_OPPOSED


def handle_sword_dance(player_state, phrase_input, world_map, current_tick, action_queue, technique_manager=None, equipment_engine=None, combat_engine=None):
    """Handle sword dance phrase input.
    
    Player types the first phrase to start the technique.
    Subsequent phrases auto-advance each tick.
    """
    player_id = player_state.get("id", "player")
    
    # Check technique ownership
    if technique_manager:
        if not technique_manager.has_technique(player_id, "sword_dance"):
            return {
                "success": False,
                "message": "You do not know the Sword Dance technique.",
                "events": []
            }

    # Check if player has an active sword dance action
    existing = action_queue.get_actor_action(player_id)
    
    if existing and existing.get("action_type") == "sword_dance":
        # Already in sword dance - ignore extra input
        return {
            "success": False,
            "message": "You are already performing Sword Dance. Wait for it to complete.",
            "events": []
        }
    
    # No active sword dance - check if this is the first phrase to start it
    # Check for sword equipped
    if equipment_engine:
        equipped = equipment_engine.get_equipped_item(player_id, "main_hand")
        if not equipped:
            return {
                "success": False,
                "message": "You need a sword equipped to use Sword Dance.",
                "events": []
            }
        from engine.items import get_item_definition
        item_def = get_item_definition(equipped.get("item_id", ""))
        if not item_def or item_def.get("subtype") != "sword":
            return {
                "success": False,
                "message": "You need a sword equipped to use Sword Dance.",
                "events": []
            }
    
    # Try to find target from the phrase (look for actor names in the phrase)
    target_data = None
    target_id = None
    
    # Search for known targets in the phrase
    if world_map:
        # Check creatures
        for creature_id, creature in world_map.get("creatures", {}).items():
            if creature_id.lower() in phrase_input.lower():
                target_data = creature
                target_id = creature_id
                break
        
        # Check NPCs
        if not target_data:
            for npc_id, npc in world_map.get("npcs", {}).items():
                if npc_id.lower() in phrase_input.lower():
                    target_data = npc
                    target_id = npc_id
                    break
        
        # Check actors
        if not target_data:
            for actor_id, actor in world_map.get("actors", {}).items():
                if actor_id.lower() in phrase_input.lower():
                    target_data = actor
                    target_id = actor_id
                    break
    
    if not target_data:
        return {
            "success": False,
            "message": "You must name your target in the phrase.",
            "events": []
        }
    
    # Define the 3 phrases for each stage
    target_name = target_data.get("name", target_id)
    phrases = [
        f"Step inside {target_name}'s guard and carve a silver arc across their flank.",
        f"Pivot on your heel and drive a rising thrust toward {target_name}'s centerline.",
        f"Complete the dance with a spinning cut aimed at {target_name}'s exposed side."
    ]
    
    # Check if input matches first phrase
    if phrase_input.lower().strip() != phrases[0].lower().strip():
        return {
            "success": False,
            "message": f"Wrong opening phrase! You must begin with: '{phrases[0]}'",
            "events": []
        }
    
    # Create Long Action for sword dance (3 ticks)
    action = action_queue.queue_action(
        actor_id=player_id,
        action_type="sword_dance",
        duration_ticks=3,
        current_tick=current_tick,
        target=target_data,
        parameters={
            "target_id": target_id,
            "target_name": target_name,
            "stage": 1,
            "phrases": phrases,
        },
        resolution_config={
            "action_type": ACTION_TYPE_OPPOSED,
            "attribute_name": "dexterity",
            "target_attribute_name": "observation",
            "technique_name": "sword_dance",
        }
    )

    if not action:
        return {
            "success": False,
            "message": "Failed to start Sword Dance.",
            "events": []
        }

    return {
        "success": True,
        "message": "",  # No message - damage only
        "action_id": action["action_id"],
        "events": []
    }


def resolve_sword_dance(action, player_state, world_map, current_tick, combat_engine, technique_engine=None, actor_positions=None, get_actors_at_position_func=None):
    """Resolve a completed sword dance action.
    
    Phase 1: Damage
    Phase 2: Taunt
    Phase 3: AoE damage + Taunt
    NO MESSAGES - only damage shows on target
    """
    target_data = action.get("target", {})
    target_id = action.get("parameters", {}).get("target_id", "")
    target_name = action.get("parameters", {}).get("target_name", target_id)
    stage = action.get("parameters", {}).get("stage", 1)
    phrases = action.get("parameters", {}).get("phrases", [])

    # Run action resolution
    resolution = resolve_action(
        action_type=ACTION_TYPE_OPPOSED,
        actor=player_state,
        attribute_name="dexterity",
        target=target_data,
        target_attribute_name="observation",
        technique_name="sword_dance",
    )

    outcome = resolution["outcome"]

    if stage == 1:
        # Phase 1: Damage only
        if outcome in ("success", "exceptional_success", "partial_success"):
            base_damage = 14
            combat_engine.attack(
                attacker_id=player_state.get("id", "player"),
                target_id=target_id,
                current_tick=current_tick,
                attacker_data=player_state,
                target_data=target_data,
                weapon_damage=base_damage,
                attack_profile={
                    "id": "sword_dance_phase1",
                    "name": "Sword Dance Phase 1",
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
    
    elif stage == 2:
        # Phase 2: Taunt only
        if combat_engine:
            combat_engine.add_taunt(target_id, player_state.get("id", "player"), 150)
    
    elif stage == 3:
        # Phase 3: AoE damage + Taunt
        if outcome in ("success", "exceptional_success", "partial_success"):
            base_damage = 28
            
            # Hit primary target
            combat_engine.attack(
                attacker_id=player_state.get("id", "player"),
                target_id=target_id,
                current_tick=current_tick,
                attacker_data=player_state,
                target_data=target_data,
                weapon_damage=base_damage,
                attack_profile={
                    "id": "sword_dance_phase3",
                    "name": "Sword Dance Phase 3",
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
            
            # Add taunt
            if combat_engine:
                combat_engine.add_taunt(target_id, player_state.get("id", "player"), 300)
            
            # AoE: Hit all other actors at same position
            if actor_positions and get_actors_at_position_func:
                player_pos = actor_positions.get(player_state.get("id", "player"))
                if player_pos:
                    actors_here = get_actors_at_position_func(player_pos.get('map_id'), player_pos.get('node_id'))
                    for other_id in actors_here:
                        if other_id != player_state.get("id", "player") and other_id != target_id:
                            other_data = find_target(other_id, world_map)
                            if other_data:
                                combat_engine.attack(
                                    attacker_id=player_state.get("id", "player"),
                                    target_id=other_id,
                                    current_tick=current_tick,
                                    attacker_data=player_state,
                                    target_data=other_data,
                                    weapon_damage=base_damage,
                                    attack_profile={
                                        "id": "sword_dance_aoe",
                                        "name": "Sword Dance AoE",
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

    # No messages - damage only
    return {
        "outcome": outcome,
        "message": "",  # Empty message - no spam
        "resolution": resolution,
        "next_stage": stage + 1 if stage < 3 else None,
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