import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.combat_techniques import CombatTechniqueEngine, TECHNIQUE_TRACK_PREY

def handle_track_prey(player_state, phrase_input, world_map, current_tick,
                      action_queue, technique_manager=None, equipment_engine=None,
                      combat_engine=None):
    player_id = player_state.get("id", "player")
    if technique_manager and not technique_manager.has_technique(player_id, "track_prey"):
        return {"success": False, "message": "You do not know Track Prey.", "events": []}
    
    target_data, target_id = find_target(phrase_input, world_map)
    if not target_data:
        return {"success": False, "message": "Name your target.", "events": []}
    
    if combat_engine and hasattr(combat_engine, '_technique_engine'):
        return combat_engine._technique_engine.use_technique(
            actor_id=player_id, technique_id="track_prey", target_id=target_id,
            actor_data=player_state, target_data=target_data,
            equipment_engine=equipment_engine, current_tick=current_tick, instant=False
        )
    return {"success": False, "message": "Combat system unavailable.", "events": []}

def find_target(phrase, world_map):
    if not world_map: return None, None
    phrase = phrase.lower()
    for cid, c in world_map.get("creatures", {}).items():
        if cid.lower() in phrase or c.get("name","").lower() in phrase: return c, cid
    for nid, n in world_map.get("npcs", {}).items():
        if nid.lower() in phrase or n.get("name","").lower() in phrase: return n, nid
    for aid, a in world_map.get("actors", {}).items():
        if aid.lower() in phrase or a.get("name","").lower() in phrase: return a, aid
    return None, None