"""
Divine Shield Command (Divine Technique)

Real command: cast divine shield

Creates a protective barrier of holy light.
Requires: Holy symbol and 2 holy water.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.combat_techniques import CombatTechniqueEngine, TECHNIQUE_DIVINE_SHIELD


def handle_divine_shield(player_state, phrase_input, world_map, current_tick,
                         action_queue, technique_manager=None, equipment_engine=None,
                         combat_engine=None):
    """Handle divine shield casting."""
    player_id = player_state.get("id", "player")

    if technique_manager and not technique_manager.has_technique(player_id, "divine_shield"):
        return {
            "success": False,
            "message": "You do not know the Divine Shield technique.",
            "events": []
        }

    if combat_engine and hasattr(combat_engine, '_technique_engine'):
        result = combat_engine._technique_engine.use_technique(
            actor_id=player_id,
            technique_id="divine_shield",
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