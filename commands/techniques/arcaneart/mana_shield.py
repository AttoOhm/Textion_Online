"""
Mana Shield Command (Arcane Technique)

Real command: cast mana shield

Creates a protective barrier of arcane energy.
Requires: Arcane focus (staff/wand) and 2 runestones.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.combat_techniques import CombatTechniqueEngine, TECHNIQUE_MANA_SHIELD


def handle_mana_shield(player_state, phrase_input, world_map, current_tick,
                       action_queue, technique_manager=None, equipment_engine=None,
                       combat_engine=None):
    """Handle mana shield casting."""
    player_id = player_state.get("id", "player")

    # Check technique ownership
    if technique_manager and not technique_manager.has_technique(player_id, "mana_shield"):
        return {
            "success": False,
            "message": "You do not know the Mana Shield technique.",
            "events": []
        }

    # Use technique through combat technique engine
    if combat_engine and hasattr(combat_engine, '_technique_engine'):
        result = combat_engine._technique_engine.use_technique(
            actor_id=player_id,
            technique_id="mana_shield",
            target_id=player_id,  # Self-target
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