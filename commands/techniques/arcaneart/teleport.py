"""
Teleport Command (Arcane Technique)

Real command: cast teleport

Instantly teleport a short distance.
Requires: Arcane focus (staff/wand) and 1 runestone.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.combat_techniques import CombatTechniqueEngine, TECHNIQUE_TELEPORT


def handle_teleport(player_state, phrase_input, world_map, current_tick,
                    action_queue, technique_manager=None, equipment_engine=None,
                    combat_engine=None):
    """Handle teleport casting."""
    player_id = player_state.get("id", "player")

    if technique_manager and not technique_manager.has_technique(player_id, "teleport"):
        return {
            "success": False,
            "message": "You do not know the Teleport technique.",
            "events": []
        }

    if combat_engine and hasattr(combat_engine, '_technique_engine'):
        result = combat_engine._technique_engine.use_technique(
            actor_id=player_id,
            technique_id="teleport",
            target_id=player_id,
            actor_data=player_state,
            target_data=player_state,
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