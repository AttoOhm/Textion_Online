import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.combat_techniques import CombatTechniqueEngine, TECHNIQUE_BEAR_TRAP

def handle_bear_trap(player_state, phrase_input, world_map, current_tick,
                      action_queue, technique_manager=None, equipment_engine=None,
                      combat_engine=None):
    player_id = player_state.get("id", "player")
    if technique_manager and not technique_manager.has_technique(player_id, "bear_trap"):
        return {"success": False, "message": "You do not know Bear Trap.", "events": []}
    
    if combat_engine and hasattr(combat_engine, '_technique_engine'):
        return combat_engine._technique_engine.use_technique(
            actor_id=player_id, technique_id="bear_trap", target_id=player_id,
            actor_data=player_state, target_data=player_state,
            equipment_engine=equipment_engine, current_tick=current_tick, instant=False
        )
    return {"success": False, "message": "Combat system unavailable.", "events": []}