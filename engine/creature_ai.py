"""
Creature AI System - Simplified

States: PATROL, COMBAT, FLEE
"""

import random
from typing import Dict, List, Any, Optional


class CreatureAI:
    """Simple creature AI - 3 states only."""

    STATE_PATROL = "patrol"
    STATE_COMBAT = "combat"
    STATE_FLEE = "flee"

    def __init__(self, world_maps, actor_positions, get_actors_at_position, get_npc_data, technique_engine=None, combat_engine=None):
        self._world_maps = world_maps
        self._actor_positions = actor_positions
        self._get_actors_at_position = get_actors_at_position
        self._get_npc_data = get_npc_data
        self._technique_engine = technique_engine
        self._combat_engine = combat_engine

        # Per-creature state
        self._ai_state: Dict[str, str] = {}
        self._spawn_info: Dict[str, Dict] = {}  # actor_id -> {map_id, node_id, max_distance}
        self._combat_target: Dict[str, Optional[str]] = {}
        self._last_technique_tick: Dict[str, int] = {}
        self._combat_group: Dict[str, Optional[str]] = {}  # actor_id -> group_leader_id

    def register_creature(self, actor_id: str, spawn_map: str = None, spawn_node: str = None, max_distance: int = 3):
        """Register a creature - starts in PATROL mode."""
        # If spawn info not provided, get from current position
        if not spawn_map or not spawn_node:
            # Try to get from current position
            current_pos = self._actor_positions.get(actor_id)
            if current_pos:
                spawn_map = current_pos.get('map_id', 'overworld')
                spawn_node = current_pos.get('node_id', 'village_center')
            else:
                spawn_map = spawn_map or 'overworld'
                spawn_node = spawn_node or 'village_center'
        
        self._spawn_info[actor_id] = {
            'map_id': spawn_map,
            'node_id': spawn_node,
            'max_distance': max_distance
        }
        if actor_id not in self._ai_state:
            self._ai_state[actor_id] = self.STATE_PATROL

    def unregister_creature(self, actor_id: str):
        """Remove creature from AI tracking."""
        for d in [self._ai_state, self._spawn_info, self._combat_target, 
                  self._last_technique_tick, self._combat_group]:
            d.pop(actor_id, None)

    def update(self, actor_id: str, actor_data: Dict, current_tick: int, socketio=None) -> Optional[Dict[str, Any]]:
        """Main AI update - call each tick for each creature."""
        state = self._ai_state.get(actor_id, self.STATE_PATROL)

        if state == self.STATE_PATROL:
            return self._update_patrol(actor_id, actor_data, current_tick)
        elif state == self.STATE_COMBAT:
            return self._update_combat(actor_id, actor_data, current_tick)
        elif state == self.STATE_FLEE:
            return self._update_flee(actor_id, actor_data, current_tick)
        return None

    def _update_patrol(self, actor_id: str, actor_data: Dict, current_tick: int) -> Optional[Dict]:
        """Patrol: 15% chance to move, check for enemies."""
        pos = self._actor_positions.get(actor_id)
        if not pos:
            return None

        # 15% chance to move
        if random.random() < 0.15:
            self._move_randomly(actor_id, pos)

        # Check for enemies at current position
        actors_here = self._get_actors_at_position(pos['map_id'], pos['node_id'])
        
        for other_id in actors_here:
            if other_id == actor_id:
                continue
            
            if self._is_enemy(actor_id, actor_data, other_id):
                # Found enemy - start combat and attack immediately!
                self._combat_target[actor_id] = other_id
                self._ai_state[actor_id] = self.STATE_COMBAT
                # Attack immediately in the same tick!
                return self._update_combat(actor_id, actor_data, current_tick)
        
        return None

    def _update_combat(self, actor_id: str, actor_data: Dict, current_tick: int) -> Optional[Dict]:
        """Combat: use techniques, check if should flee, check if target fled."""
        target_id = self._combat_target.get(actor_id)
        
        # Check if target is still valid
        if not target_id or not self._is_target_valid(actor_id, target_id):
            # Target gone, back to patrol
            self._combat_target[actor_id] = None
            self._ai_state[actor_id] = self.STATE_PATROL
            return None
        
        # Decay threat on target (taunt decays -100 per tick)
        if hasattr(self, '_combat_engine') and self._combat_engine:
            self._combat_engine.decay_threat(actor_id)
        
        # Check if we should switch target (someone has more threat)
        if hasattr(self, '_combat_engine') and self._combat_engine:
            highest_threat_attacker, highest_threat = self._combat_engine.get_highest_threat(actor_id)
            current_threat = self._combat_engine.get_threat(actor_id, target_id)
            
            # Switch to highest threat target if it's not our current target
            if highest_threat_attacker and highest_threat_attacker != target_id and highest_threat > current_threat:
                self._combat_target[actor_id] = highest_threat_attacker
                target_id = highest_threat_attacker
        
        # Check if target fled (poursuit check)
        target_pos = self._actor_positions.get(target_id)
        my_pos = self._actor_positions.get(actor_id)
        if target_pos and my_pos and (target_pos['map_id'] != my_pos['map_id'] or target_pos['node_id'] != my_pos['node_id']):
            # Target is in different location - check if we should pursue
            poursuit = actor_data.get('poursuit', False)
            if poursuit and random.random() < 0.75:
                # 75% chance to pursue - move to target's location
                self._actor_positions[actor_id] = {
                    'map_id': target_pos['map_id'],
                    'node_id': target_pos['node_id']
                }
                #print(f"[AI] {actor_id} pursuing {target_id} to {target_pos['map_id']}/{target_pos['node_id']}")
            else:
                # Give up chase
                self._combat_target[actor_id] = None
                self._ai_state[actor_id] = self.STATE_PATROL
                #print(f"[AI] {actor_id} lost track of {target_id}")
                return None
        
        # Check if should flee (flee:0 = never, flee:20 = below 20% HP, flee:50 = below 50% HP)
        # Support both 'flee' (new) and 'flee_threshold' (old) for backward compatibility
        flee_threshold = actor_data.get('flee', actor_data.get('flee_threshold', 0))
        if flee_threshold > 0:
            hp = actor_data.get('hp', 100)
            max_hp = actor_data.get('max_hp', 100)
            hp_ratio = hp / max_hp if max_hp > 0 else 1.0
            
            if hp_ratio <= (flee_threshold / 100.0):
                # Flee!
                self._ai_state[actor_id] = self.STATE_FLEE
                #print(f"[AI] {actor_id} fleeing (HP {hp}/{max_hp}, threshold {flee_threshold}%)")
                return None
        
        # Use technique if engine available (only ONE per tick)
        if self._technique_engine:
            last_tick = self._last_technique_tick.get(actor_id, -1)
            if last_tick != current_tick:
                target_data = self._get_npc_data(target_id) or {}
                result = self._use_technique(actor_id, actor_data, target_id, target_data, current_tick)
                if result and result.get('technique'):
                    self._last_technique_tick[actor_id] = current_tick
                    return result
        return None

    def _update_flee(self, actor_id: str, actor_data: Dict, current_tick: int) -> Optional[Dict]:
        """Flee: move to random adjacent node, then back to patrol."""
        pos = self._actor_positions.get(actor_id)
        if not pos:
            self._ai_state[actor_id] = self.STATE_PATROL
            return None

        # Get adjacent nodes
        node_data = self._world_maps.get(pos['map_id'], {}).get('nodes', {}).get(pos['node_id'], {})
        exits = node_data.get('exits', {})
        
        if not exits:
            # No exits, can't flee
            self._ai_state[actor_id] = self.STATE_PATROL
            return None
        
        # Pick random adjacent node
        random_node = random.choice(list(exits.values()))
        self._actor_positions[actor_id] = {
            'map_id': pos['map_id'],
            'node_id': random_node
        }
        
        # After fleeing, go back to patrol
        self._ai_state[actor_id] = self.STATE_PATROL
        self._combat_target[actor_id] = None
        #print(f"[AI] {actor_id} fled to {random_node}")
        return None

    def _move_randomly(self, actor_id: str, pos: Dict) -> None:
        """Move actor to random adjacent node within patrol radius."""
        spawn = self._spawn_info.get(actor_id)
        if not spawn:
            return

        current_node = pos['node_id']
        node_data = self._world_maps.get(pos['map_id'], {}).get('nodes', {}).get(current_node, {})
        exits = node_data.get('exits', {})
        
        if not exits:
            return
        
        # Get all possible nodes to move to
        candidates = list(exits.values())
        
        # Filter by distance from spawn (BFS)
        spawn_node = spawn['node_id']
        max_dist = spawn.get('max_distance', 3)
        valid = []
        for node in candidates:
            dist = self._node_distance(spawn_node, node, pos['map_id'])
            if dist <= max_dist:
                valid.append(node)
        
        if not valid:
            if max_dist == 0:
                return  # Don't move if max_distance is 0 (stationary NPC)
            valid = candidates  # fallback to any exit only if max_distance > 0
        
        # Move to random valid node
        new_node = random.choice(valid)
        self._actor_positions[actor_id] = {
            'map_id': pos['map_id'],
            'node_id': new_node
        }

    def _node_distance(self, from_node: str, to_node: str, map_id: str) -> int:
        """BFS distance between two nodes."""
        if from_node == to_node:
            return 0
        nodes = self._world_maps.get(map_id, {}).get('nodes', {})
        visited = {from_node}
        queue = [(from_node, 0)]
        while queue:
            node, dist = queue.pop(0)
            for next_node in nodes.get(node, {}).get('exits', {}).values():
                if next_node == to_node:
                    return dist + 1
                if next_node not in visited:
                    visited.add(next_node)
                    queue.append((next_node, dist + 1))
        return 999

    def _is_enemy(self, actor_id: str, actor_data: Dict, target_id: str) -> bool:
        """Check if target is an enemy based on relationships."""
        target_data = self._get_npc_data(target_id) or {}
        relationships = actor_data.get('relationships', {})
        
        # Check if target is a player (not in NPC data)
        is_player = not target_data or target_data.get('type') != 'creature'
        
        if is_player:
            # Check if relationship says "player": "enemies"
            if 'player' in relationships:
                return relationships['player'] == 'enemies'
            # Default: hostile creatures attack players
            return actor_data.get('is_hostile', False)
        else:
            # Target is a creature/NPC - check by race/species
            target_race = target_data.get('race', '')
            if target_race and target_race in relationships:
                return relationships[target_race] == 'enemies'
            
            target_species = target_data.get('species', '')
            if target_species and target_species in relationships:
                return relationships[target_species] == 'enemies'
            
            # Check by exact ID
            if target_id in relationships:
                return relationships[target_id] == 'enemies'
            
            # Default hostility
            if actor_data.get('is_hostile', False):
                return target_data.get('is_hostile', False)
        
        return False

    def _is_target_valid(self, actor_id: str, target_id: str) -> bool:
        """Check if target is still a valid combat target."""
        # Check if target is a player (not in NPC data)
        target_data = self._get_npc_data(target_id)
        if not target_data:
            # Player - check if in same map
            pos = self._actor_positions.get(target_id)
            if not pos:
                return False
            my_pos = self._actor_positions.get(actor_id)
            if not my_pos:
                return False
            return pos['map_id'] == my_pos['map_id']
        
        # NPC - check HP and position
        if target_data.get('hp', 0) <= 0:
            return False
        pos = self._actor_positions.get(target_id)
        if not pos:
            return False
        my_pos = self._actor_positions.get(actor_id)
        if not my_pos:
            return False
        return pos['map_id'] == my_pos['map_id']

    def _is_target_in_same_node(self, actor_id: str, target_id: str) -> bool:
        """Check if target is in the same map node as actor."""
        actor_pos = self._actor_positions.get(actor_id)
        target_pos = self._actor_positions.get(target_id)
        if not actor_pos or not target_pos:
            return False
        return actor_pos['map_id'] == target_pos['map_id'] and actor_pos['node_id'] == target_pos['node_id']

    def _is_target_adjacent(self, actor_id: str, target_id: str) -> bool:
        """Check if target is in an adjacent node (BFS distance = 1)."""
        actor_pos = self._actor_positions.get(actor_id)
        target_pos = self._actor_positions.get(target_id)
        if not actor_pos or not target_pos:
            return False
        if actor_pos['map_id'] != target_pos['map_id']:
            return False
        
        node_data = self._world_maps.get(actor_pos['map_id'], {}).get('nodes', {}).get(actor_pos['node_id'], {})
        exits = node_data.get('exits', {})
        return target_pos['node_id'] in exits.values()

    def _use_technique(self, actor_id: str, actor_data: Dict, target_id: str, target_data: Dict, current_tick: int) -> Optional[Dict]:
        """Select and use a smart technique based on distance and role."""
        techniques = actor_data.get('techniques', [])
        if not techniques:
            return None
        
        # Analyze combat role from available techniques
        has_ranged = any(t == 'short_bow_shot' for t in techniques)
        has_shield_bash = any(t == 'shield_bash' for t in techniques)
        has_crunch = any(t == 'crunch' for t in techniques)
        has_melee_attack = any(t == 'melee_attack' for t in techniques)
        
        in_same_node = self._is_target_in_same_node(actor_id, target_id)
        is_adjacent = self._is_target_adjacent(actor_id, target_id)
        
        # Determine distance
        if in_same_node:
            distance = "melee"  # Same node = close combat
        elif is_adjacent:
            distance = "adjacent"  # Adjacent node = medium range
        else:
            distance = "far"  # Further away = long range
        
        # Smart technique selection based on creature role and distance
        chosen = None
        
        if has_ranged:
            # Archer/Ranged role
            if distance in ("adjacent", "far"):
                # Shoot from range
                chosen = 'short_bow_shot'
            else:
                # Enemy is in same node - switch to melee
                if 'melee_attack' in techniques:
                    chosen = 'melee_attack'
                elif 'bite' in techniques:
                    chosen = 'bite'
                else:
                    chosen = random.choice(techniques)
        elif has_shield_bash:
            # Guard/Shield role: bash on cooldown, melee otherwise
            if distance == "melee":
                # Check if shield_bash is off cooldown
                if self._technique_engine._cooldowns.can_use(actor_id, 'shield_bash', current_tick):
                    chosen = 'shield_bash'
                elif has_crunch:
                    chosen = 'crunch'
                else:
                    chosen = random.choice([t for t in techniques if t != 'shield_bash'] or techniques)
            else:
                # Move toward target (use patrol movement)
                # But still use a technique if possible
                if has_crunch:
                    chosen = 'crunch'
                else:
                    chosen = random.choice(techniques)
        else:
            # Default: prefer different techniques based on distance
            if distance == "melee":
                # Close range: prefer bite/claw/crunch over bow
                melee_techs = [t for t in techniques if t != 'short_bow_shot']
                if melee_techs and random.random() < 0.7:
                    # 70% chance to pick a melee technique
                    chosen = random.choice(melee_techs)
                else:
                    chosen = random.choice(techniques)
            else:
                # At range: try ranged first, fallback to any
                ranged_techs = [t for t in techniques if t == 'short_bow_shot']
                if ranged_techs:
                    chosen = ranged_techs[0]
                else:
                    chosen = random.choice(techniques)
        
        # Use the chosen technique
        result = self._technique_engine.use_technique(
            actor_id=actor_id,
            technique_id=chosen,
            target_id=target_id,
            actor_data=actor_data,
            target_data=target_data,
            current_tick=current_tick,
            instant=True,
        )
        return result

    def get_state(self, actor_id: str) -> str:
        """Get current AI state."""
        return self._ai_state.get(actor_id, self.STATE_PATROL)

    def set_combat_target(self, actor_id: str, target_id: str):
        """Set combat target and switch to combat state."""
        self._combat_target[actor_id] = target_id
        self._ai_state[actor_id] = self.STATE_COMBAT

    def clear_combat_target(self, actor_id: str):
        """Clear combat target and return to patrol."""
        self._combat_target[actor_id] = None
        self._ai_state[actor_id] = self.STATE_PATROL