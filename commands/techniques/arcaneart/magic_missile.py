"""
Magic Missile Command (Arcane Technique)

Real command: cast magic missile <target>

Launches a bolt of arcane energy that always hits.
Requires: Arcane focus (staff/wand) and 1 runestone.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.combat_techniques import CombatTechniqueEngine, TECHNIQUE_MAGIC_MISSILE


def handle_magic_missile(player_state, phrase_input, world_map, current_tick, 
                         action_queue, technique_manager=None, equipment_engine=None, 
                         combat_engine=None):
    """Handle magic missile casting."""
    player_id = player_state.get("id", "player")

    # Check technique ownership
    if technique_manager and not technique_manager.has_technique(player_id, "magic_missile"):
        return {
            "success": False,
            "message": "You do not know the Magic Missile technique.",
            "events": []
        }

    # Find target
    target_data, target_id = find_target_from_phrase(phrase_input, world_map)
    if not target_data:
        return {
            "success": False,
            "message": "You must name your target.",
            "events": []
        }

    # Use technique through combat technique engine
    if combat_engine and hasattr(combat_engine, '_technique_engine'):
        result = combat_engine._technique_engine.use_technique(
            actor_id=player_id,
            technique_id="magic_missile",
            target_id=target_id,
            actor_data=player_state,
            target_data=target_data,
            equipment_engine=equipment_engine,
            current_tick=current_tick,
            instant=False
        )
        return result

    return {
        "success": False,
        "message": "Combat system not available.",
        "events": []
    }


def find_target_from_phrase(phrase, world_map):
    """Find a target from the command phrase."""
    if not world_map:
        return None, None

    phrase_lower = phrase.lower()

    # Check creatures
    for creature_id, creature in world_map.get("creatures", {}).items():
        if creature_id.lower() in phrase_lower or creature.get("name", "").lower() in phrase_lower:
            return creature, creature_id

    # Check NPCs
    for npc_id, npc in world_map.get("npcs", {}).items():
        if npc_id.lower() in phrase_lower or npc.get("name", "").lower() in phrase_lower:
            return npc, npc_id

    # Check actors
    for actor_id, actor in world_map.get("actors", {}).items():
        if actor_id.lower() in phrase_lower or actor.get("name", "").lower() in phrase_lower:
            return actor, actor_id

    return None, None