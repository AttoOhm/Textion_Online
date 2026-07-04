import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.combat_techniques import CombatTechniqueEngine, TECHNIQUE_LOOT

def handle_loot(player_state, phrase_input, world_map, current_tick,
                action_queue, technique_manager=None, equipment_engine=None,
                combat_engine=None):
    """Hunter technique: Loot a corpse to take all available items.
    
    Allows hunters to loot corpses efficiently. Can loot both creature and player corpses.
    """
    player_id = player_state.get("id", "player")
    if technique_manager and not technique_manager.has_technique(player_id, "loot"):
        return {"success": False, "message": "You do not know the Loot technique.", "events": []}
    
    if not phrase_input:
        return {"success": False, "message": "Loot what?", "events": []}
    
    # Import the loot handler from world routes
    from server.routes.world import _handle_take
    
    # Get player state and find corpse
    from server.state import get_player_state, corpses
    state = get_player_state(player_id)
    
    # Find the corpse
    loot_target = phrase_input.lower().replace(' ', '_')
    result = _handle_take(player_id, loot_target, state)
    
    if result.get('error'):
        return {"success": False, "message": result['error'], "events": []}
    
    return {"success": True, "message": result.get('message', ''), "events": []}