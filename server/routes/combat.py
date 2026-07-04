"""
Combat routes - attack command, combat engine, creature death handling.
"""

import re
from flask import request
from flask_socketio import emit
from server.state import (
    socketio, player_sessions, player_states
)
from server.state import get_player_state, get_npc_data, get_creature_display_name
from server.state import ACTOR_POSITIONS, corpses, creature_death_times, CREATURE_INSTANCES
from server.state import tick_number, _quest_cache
from server.state import get_actors_at_position
from server.state import _update_quest_kill_progress
from engine.attributes import get_attribute_with_buffs


@socketio.on('command')
def handle_command(command):
    """Handle combat commands - DEPRECATED: Use world_command instead.
    
    This handler is kept for backward compatibility but attack commands
    are now handled by world_command in world.py to avoid duplicate queuing.
    """
    pass


def _handle_player_death(player_id, state, map_id, node_id, combat_engine, current_tick):
    """Handle player death - create corpse, respawn at graveyard.
    
    Creates a player corpse with:
    - All inventory items (only lootable by the player)
    - All money
    - One random equipped item (lootable by anyone)
    """
    import random
    import server.state as st
    
    # Get player's inventory and equipment
    inventory = state.get('inventory', [])
    equipment = state.get('equipment', {})
    coins = state.get('coins', 0)
    
    # Create corpse loot table
    corpse_loot = []
    
    # Add all inventory items (player-only loot)
    for item in inventory:
        if isinstance(item, dict):
            corpse_loot.append({
                'item_id': item.get('item_id', item.get('name', '')),
                'name': item.get('name', 'Unknown Item'),
                'quantity': item.get('quantity', 1),
                'owner_only': True  # Only the player who died can loot this
            })
        else:
            corpse_loot.append({
                'item_id': item,
                'name': item,
                'quantity': 1,
                'owner_only': True
            })
    
    # Add coins to loot
    if coins > 0:
        corpse_loot.append({
            'item_id': 'coins',
            'name': f'{coins} coins',
            'quantity': coins,
            'owner_only': True
        })
    
    # Select one random equipped item to make publicly lootable
    equipped_items = []
    for slot, item in equipment.items():
        if item and isinstance(item, dict):
            equipped_items.append({
                'slot': slot,
                'item_id': item.get('item_id', ''),
                'name': item.get('name', 'Unknown'),
                'owner_only': False  # Anyone can loot this
            })
    
    if equipped_items:
        random_equip = random.choice(equipped_items)
        corpse_loot.append(random_equip)
        print(f"[DEATH] Player {player_id} died. Random equipped item '{random_equip['name']}' is now public loot.")
    
    # Create player corpse
    player_name = state.get('name', player_id)
    corpses[player_id] = {
        'map_id': map_id,
        'node_id': node_id,
        'loot_table': corpse_loot,
        'display_name': f"{player_name}'s corpse",
        'actor_id': player_id,
        'is_player_corpse': True,
        'owner_id': player_id
    }
    
    print(f"[DEATH] Player {player_name} died at {map_id}/{node_id}. Corpse created with {len(corpse_loot)} items.")
    
    # Clear player inventory and equipment
    state['inventory'] = []
    state['equipment'] = {slot: None for slot in ['main_hand', 'off_hand', 'armor', 'accessory']}
    state['coins'] = 0
    
    # Respawn player at graveyard
    graveyard_pos = {'map_id': 'village', 'node_id': 'graveyard'}
    state['position'] = graveyard_pos
    st.ACTOR_POSITIONS[player_id] = graveyard_pos
    
    # Restore player HP to 50% of max
    max_hp = state.get('max_hp', 100)
    state['hp'] = max_hp // 2
    
    # End combat
    state['in_combat'] = False
    state['combat_target'] = None
    
    # Sync HP in combat engine
    if combat_engine.has_actor(player_id):
        combat_engine._hp[player_id]['current'] = state['hp']
    
    print(f"[DEATH] Player {player_name} respawned at village/graveyard with {state['hp']} HP.")


def process_attack_command(player_id, command):
    """Process a queued attack command during tick."""
    import re
    from server.state import WORLD_MAPS
    from engine.combat import CombatEngine
    from engine.equipment import EquipmentEngine
    from engine.creature_ai import CreatureAI
    
    state = get_player_state(player_id)
    cmd = command.strip().lower()
    cmd_parts = cmd.split()
    
    if cmd_parts[0] != 'attack' or len(cmd_parts) < 2:
        return
    
    target_name = ' '.join(cmd_parts[1:]).lower().replace(' ', '_')
    pos = state.get('position', {'map_id': 'village', 'node_id': 'village_center'})
    p_map, p_node = pos['map_id'], pos['node_id']
    actors_here = get_actors_at_position(p_map, p_node)
    
    # Match target
    matched_actor_id = None
    for actor_id in actors_here:
        # Direct ID match (exact)
        if actor_id.lower() == target_name:
            matched_actor_id = actor_id
            break
        # ID match with numeric suffix (e.g., "grey_wolf" matches "grey_wolf_1")
        actor_id_base = actor_id.lower()
        # Remove trailing _1, _2, etc. from actor ID
        actor_id_clean = re.sub(r'_\d+$', '', actor_id_base)
        if actor_id_clean == target_name:
            matched_actor_id = actor_id
            break
        # Partial ID match (e.g., "grey" matches "grey_wolf_1")
        if target_name in actor_id_base:
            matched_actor_id = actor_id
            break
        # Display name match
        act_data = get_npc_data(actor_id)
        if act_data:
            display_name = get_creature_display_name(actor_id, state) if act_data.get('type') == 'creature' else actor_id
            # Normalize: lowercase, replace spaces with underscores, remove articles
            display_norm = display_name.lower().replace(' ', '_')
            # Remove leading articles (a_, an_, the_)
            for article in ['a_', 'an_', 'the_']:
                if display_norm.startswith(article):
                    display_norm = display_norm[len(article):]
                    break
            target_norm = target_name.lower().replace(' ', '_')
            # Check exact match or if target is contained in display name
            if display_norm == target_norm or target_norm in display_norm:
                matched_actor_id = actor_id
                break
    
    if not matched_actor_id:
        socketio.emit('command_result', {'error': f"Target '{target_name.replace('_', ' ').title()}' is not here to attack."})
        return
    
    # Initialize combat engines if needed
    if not hasattr(socketio, 'combat_engine'):
        socketio.combat_engine = CombatEngine()
    if not hasattr(socketio, 'equipment_engine'):
        socketio.equipment_engine = EquipmentEngine()
    if not hasattr(socketio, 'creature_ai'):
        from engine.combat_techniques import CombatTechniqueEngine
        from engine.effects import EffectEngine
        from engine.long_action import ActionQueue
        from engine.creature_ai import CreatureAI
        from server.state import technique_manager, resource_node_manager, WORLD_MAPS
        technique_engine = CombatTechniqueEngine(
            socketio.combat_engine,
            technique_manager,
            EffectEngine(),
            ActionQueue()
        )
        def get_player_race(pid):
            # Check if pid is in player_states to determine if they're a player
            if isinstance(pid, str) and pid in player_states:
                return player_states[pid].get('race', 'player')
            return None
        
        socketio.creature_ai = CreatureAI(
            world_maps=WORLD_MAPS,
            actor_positions=ACTOR_POSITIONS,
            get_actors_at_position=get_actors_at_position,
            get_npc_data=get_npc_data,
            get_creature_display_name=get_creature_display_name,
            technique_engine=technique_engine,
            get_player_race=get_player_race
        )
    
    combat_engine = socketio.combat_engine
    equipment_engine = socketio.equipment_engine
    creature_ai = socketio.creature_ai
    
    # Sync player equipment
    from engine.equipment import VALID_SLOTS
    if player_id not in equipment_engine._equipment:
        equipment_engine._equipment[player_id] = {s: None for s in VALID_SLOTS}
    for slot, entry in state.get('equipment', {}).items():
        if entry and isinstance(entry, dict):
            equipment_engine._equipment[player_id][slot] = entry
    
    # Set player attributes (only if not already set - preserves buffs)
    if 'attributes' not in state:
        state['attributes'] = {
            "strength": 65, "dexterity": 70, "observation": 60, "constitution": 55,
            "willpower": 45, "reactiveness": 80, "arcana": 30, "knowledge": 40
        }
    
    # Initialize player in CombatEngine using real player_id
    if not combat_engine.has_actor(player_id):
        combat_engine.init_actor(player_id, max_hp=state.get('hp', 100), actor_data=state)
    else:
        combat_engine._actor_data[player_id] = state
    
    # Initialize target
    if not combat_engine.has_actor(matched_actor_id):
        matched_data = get_npc_data(matched_actor_id) or {}
        if 'attributes' not in matched_data:
            matched_data['attributes'] = {
                "strength": 50, "dexterity": 50, "observation": 50, "constitution": 50,
                "willpower": 50, "reactiveness": 50, "arcana": 50, "knowledge": 50
            }
        matched_max_hp = matched_data.get('hp', 80)
        combat_engine.init_actor(matched_actor_id, max_hp=matched_max_hp, actor_data=matched_data)
    
    # Get weapon damage from equipped weapon
    from engine.items import get_item_definition
    equipped = equipment_engine.get_equipped_item(player_id, 'main_hand')
    weapon_damage = 3  # default unarmed damage
    if equipped:
        item_id = equipped.get('item_id', '')
        item_def = get_item_definition(item_id)
        if item_def:
            weapon_damage = item_def.get('damage', 3)
    
    # Set player combat state
    state['in_combat'] = True
    state['combat_target'] = matched_actor_id
    
    # Execute attack with weapon damage as base
    attack_config = {
        "actor_attribute": "dexterity",
        "target_attribute": "observation",
    }
    
    result = combat_engine.attack(
        attacker_id=player_id,
        target_id=matched_actor_id,
        equipment_engine=equipment_engine,
        current_tick=tick_number,
        attacker_data=state,
        target_data=combat_engine.get_actor_data(matched_actor_id),
        action_config=attack_config,
        weapon_damage=weapon_damage
    )
    
    # Emit result
    socketio.emit('command_result', {'message': result.get('message')})
    
    # Debug: Show combat details
    if result:
        matched_data = get_npc_data(matched_actor_id) or {}
        debug_msg = f"[DEBUG] Attack: {result.get('message')}\n"
        debug_msg += f"[DEBUG] Hit: {result.get('hit')}, Outcome: {result.get('outcome')}\n"
        debug_msg += f"[DEBUG] Your roll: {result.get('actor_total')} (str: {get_attribute_with_buffs(state, 'strength')}, dex: {get_attribute_with_buffs(state, 'dexterity')})\n"
        debug_msg += f"[DEBUG] Wolf defense: {result.get('target_total')} (obs: {matched_data.get('attributes', {}).get('observation', 50)})\n"
        debug_msg += f"[DEBUG] Multiplier: {result.get('multiplier')}, Margin: {result.get('margin')}"
        print(debug_msg)
    
    # Creature AI: Set combat target so the tick loop will handle creature responses
    target_hp = combat_engine.get_hp(matched_actor_id)
    if target_hp['current'] > 0:
        # Set player as combat target for the creature - the tick loop will handle the AI update
        creature_ai.set_combat_target(matched_actor_id, player_id)
    
    # Sync player HP
    player_hp_data = combat_engine.get_hp(player_id)
    state['hp'] = player_hp_data['current']
    
    # Check if target died - end combat
    target_hp = combat_engine.get_hp(matched_actor_id)
    if target_hp['current'] <= 0:
        state['in_combat'] = False
        state['combat_target'] = None
        
        # Check if player died
        if matched_actor_id == player_id:
            _handle_player_death(player_id, state, p_map, p_node, combat_engine, tick_number)
            socketio.emit('command_result', {
                'message': 'You have been slain! Your corpse remains at the scene. Respawn at the graveyard.'
            })
        else:
            # CREATURE DEATH - existing logic
            target_data = get_npc_data(matched_actor_id) or {}
            loot_table = target_data.get('loot', [])
            
            # If no loot, try to load from template
            if not loot_table:
                template_id = target_data.get('template')
                if template_id:
                    import os, json
                    template_path = os.path.join('data', 'actors', f'{template_id}.json')
                    if os.path.exists(template_path):
                        with open(template_path, 'r') as tf:
                            try:
                                template_data = json.load(tf)
                                loot_table = template_data.get('loot', [])
                                print(f"[COMBAT] Loaded {len(loot_table)} loot items from template {template_id} for {matched_actor_id}")
                            except Exception as e:
                                print(f"[COMBAT] Failed to load template loot: {e}")
            
            display_name = get_creature_display_name(matched_actor_id, state) if target_data.get('type') == 'creature' else matched_actor_id
            
            # Clean display name - remove numeric suffix for better UX
            clean_display = re.sub(r'\s*\d+$', '', display_name).strip()
            
            # Roll for loot - only items that pass chance check appear on corpse
            import random
            actual_loot = []
            for loot_entry in loot_table:
                chance = loot_entry.get('chance', 1.0)
                if random.random() < chance:
                    actual_loot.append(loot_entry)
            
            # Only create corpse if it has loot
            if actual_loot:
                corpses[matched_actor_id] = {
                    'map_id': p_map,
                    'node_id': p_node,
                    'loot_table': actual_loot,
                    'display_name': clean_display,
                    'actor_id': matched_actor_id
                }
                print(f"[COMBAT] Created corpse {clean_display} with {len(actual_loot)}/{len(loot_table)} loot items")
            else:
                print(f"[COMBAT] No loot dropped for {clean_display}, not creating corpse")
            
            # Quest kill tracking
            _update_quest_kill_progress(state, matched_actor_id, target_data)
            
            # Schedule respawn for creatures
            if matched_actor_id in CREATURE_INSTANCES:
                creature_death_times[matched_actor_id] = tick_number
                import server.state as st
                if matched_actor_id in st.ACTOR_POSITIONS:
                    del st.ACTOR_POSITIONS[matched_actor_id]
                instance_data = CREATURE_INSTANCES.get(matched_actor_id, {})
                respawn_min = instance_data.get('respawn_minutes', 10)
                print(f"[DEATH] Creature '{matched_actor_id}' died. Will respawn in {respawn_min} minutes.")
            
            socketio.emit('command_result', {'message': f"{display_name} has been slain! You can now loot the corpse."})
            # Send updated world state so player can see the corpse
            from server.routes.world import build_world_update_for_state
            updated_state = get_player_state(player_id)
            world_update = build_world_update_for_state(player_id, updated_state)
            socketio.emit('world_update', world_update)
