"""
Game tick loop - extracted from server/state.py
Manages the game loop, command processing, and long action resolution.
"""

import threading
import time
from engine.long_action import process_tick


def start_tick_loop():
    """Start the game tick loop."""

    def tick_loop():
        while True:
            time.sleep(20)
            import server.state as st
            
            st.tick_number += 1
            st.game_minutes += 1
            sio = st.socketio

            from server.routes.world import _process_creature_respawns
            _process_creature_respawns()

            # Resolve completed long actions FIRST so actors are freed before new commands
            from server.routes.crafting import resolve_crafting_action
            results = process_tick(st.long_action_queue, st.tick_number, resolve_crafting_action)
            for result in results:
                if result and result.get('message') and sio:
                    actor_id = result.get('actor_id')
                    for sid, sid_pid in st.player_sessions.items():
                        sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                        if sid_pid == actor_id:
                            sio.emit('command_result', {'message': result['message']}, room=sid)
                            break
                # Auto-update inventory after any action that might change it
                if result and result.get('actor_id') and sio:
                    from server.routes.inventory import emit_inventory_update
                    actor_sid = None
                    for sid, sid_pid in st.player_sessions.items():
                        sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                        if sid_pid == result['actor_id']:
                            actor_sid = sid
                            break
                    if actor_sid:
                        emit_inventory_update(result['actor_id'], sid=actor_sid)

            # Process ONE pending command per player per tick
            for pid, cmds in list(st.pending_commands.items()):
                state = st.player_states.get(pid)
                if not state or not cmds:
                    continue
                
                cmd = cmds.pop(0)
                parts = cmd.lower().strip().split()
                action = parts[0] if parts else ''
                args = parts[1:] if len(parts) > 1 else []
                pos = state.get('position', {})

                if action == 'move' and args:
                    # Check if player is in combat
                    if state.get('in_combat', False):
                        if sio:
                            for sid, sid_pid in st.player_sessions.items():
                                sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                                if sid_pid == pid:
                                    sio.emit('command_result', {'message': 'You cannot move while in combat!'}, room=sid)
                                    break
                        continue
                    # Skip 'to' if present and join remaining words as destination
                    if args[0] == 'to' and len(args) > 1:
                        dest = ' '.join(args[1:]).lower()
                    else:
                        dest = ' '.join(args).lower()
                    map_id = pos.get('map_id', 'village')
                    node_id = pos.get('node_id', 'village_center')
                    from server.state import WORLD_MAPS
                    node_data = WORLD_MAPS.get(map_id, {}).get('nodes', {}).get(node_id)
                    if node_data:
                        exits = node_data.get('exits', {})
                        # Check exact match, normalized match, and with "to " prefix
                        dest_normalized = dest.replace(' ', '_')
                        dest_with_to = f'to {dest}' if not dest.startswith('to ') else dest
                        if dest in exits or dest_normalized in exits or dest_with_to in exits:
                            target = exits.get(dest) or exits.get(dest_normalized) or exits.get(dest_with_to)
                            state['position'] = {'map_id': map_id, 'node_id': target}
                            st.ACTOR_POSITIONS[pid] = {'map_id': map_id, 'node_id': target}
                            if sio:
                                for sid, sid_pid in st.player_sessions.items():
                                    sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                                    if sid_pid == pid:
                                        sio.emit('command_result', {'message': f'You move {dest}.'}, room=sid)
                                        break

                elif action == 'chop' and args:
                    resource_name = ' '.join(args)
                    p_map = pos.get('map_id', 'village')
                    p_node = pos.get('node_id', 'village_center')
                    from commands.techniques.crafting.chop_cmd import handle_chop
                    result = handle_chop(state, resource_name, p_map, p_node,
                                         st.resource_node_manager, None, None,
                                         st.long_action_queue, st.tick_number, pid)
                    if result and result.get('message') and sio:
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            if sid_pid == pid:
                                sio.emit('command_result', {'message': result['message']}, room=sid)
                                break

                elif action == 'mine' and args:
                    resource_name = ' '.join(args)
                    p_map = pos.get('map_id', 'village')
                    p_node = pos.get('node_id', 'village_center')
                    from commands.techniques.crafting.mine_cmd import handle_mine
                    result = handle_mine(state, resource_name, p_map, p_node,
                                         st.resource_node_manager, None, None,
                                         st.long_action_queue, st.tick_number, pid)
                    if result and result.get('message') and sio:
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            if sid_pid == pid:
                                sio.emit('command_result', {'message': result['message']}, room=sid)
                                break

                elif action == 'harvest' and args:
                    resource_name = ' '.join(args)
                    p_map = pos.get('map_id', 'village')
                    p_node = pos.get('node_id', 'village_center')
                    from commands.techniques.crafting.harvest_cmd import handle_harvest
                    result = handle_harvest(state, resource_name, p_map, p_node,
                                            st.resource_node_manager, None, None,
                                            st.long_action_queue, st.tick_number, pid)
                    if result and result.get('message') and sio:
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            if sid_pid == pid:
                                sio.emit('command_result', {'message': result['message']}, room=sid)
                                break

                elif action == 'saw' and args:
                    resource_name = ' '.join(args)
                    p_map = pos.get('map_id', 'village')
                    p_node = pos.get('node_id', 'village_center')
                    from commands.techniques.crafting.saw_cmd import handle_saw
                    # Load player inventory into the shared inventory engine
                    st.inventory_engine._inventories[pid] = state.get('inventory', [])
                    result = handle_saw(state, resource_name, p_map, p_node,
                                        st.resource_node_manager, st.inventory_engine, st.equipment_engine,
                                        st.disciplines_engine, st.long_action_queue, pid, st.tick_number)
                    # Sync back any changes (items consumed/produced)
                    state['inventory'] = st.inventory_engine._inventories.get(pid, state.get('inventory', []))
                    if result and result.get('message') and sio:
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            if sid_pid == pid:
                                sio.emit('command_result', {'message': result['message']}, room=sid)
                                break

                elif action == 'smelt' and args:
                    resource_name = ' '.join(args)
                    p_map = pos.get('map_id', 'village')
                    p_node = pos.get('node_id', 'village_center')
                    from commands.techniques.crafting.smelt_cmd import handle_smelt
                    # Load player inventory into the shared inventory engine
                    st.inventory_engine._inventories[pid] = state.get('inventory', [])
                    result = handle_smelt(state, resource_name, p_map, p_node,
                                          st.resource_node_manager, st.inventory_engine, st.equipment_engine,
                                          st.disciplines_engine, st.long_action_queue, pid, st.tick_number)
                    # Sync back any changes (items consumed/produced)
                    state['inventory'] = st.inventory_engine._inventories.get(pid, state.get('inventory', []))
                    if result and result.get('message') and sio:
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            if sid_pid == pid:
                                sio.emit('command_result', {'message': result['message']}, room=sid)
                                break

                elif action == 'grind' and args:
                    resource_name = ' '.join(args)
                    from commands.techniques.crafting.grind_cmd import handle_grind
                    result = handle_grind(state, resource_name, st.long_action_queue, st.tick_number, pid)
                    if result and result.get('message') and sio:
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            if sid_pid == pid:
                                sio.emit('command_result', {'message': result['message']}, room=sid)
                                break

                elif action == 'repair' and args:
                    resource_name = ' '.join(args)
                    from commands.techniques.crafting.repair_cmd import handle_repair
                    result = handle_repair(state, resource_name, st.long_action_queue, st.tick_number, pid)
                    if result and result.get('message') and sio:
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            if sid_pid == pid:
                                sio.emit('command_result', {'message': result['message']}, room=sid)
                                break

                elif action == 'learn' and args:
                    # Filter out 'recipe' keyword if present (handle "learn recipe oak bow" or "learn recipe: oak bow")
                    filtered_args = [arg for arg in args if arg.lower() not in ['recipe', 'recipe:']]
                    resource_name = ' '.join(filtered_args)
                    from commands.techniques.crafting.learn_cmd import handle_learn
                    from server.state import recipe_manager
                    # Load player inventory into the shared inventory engine (normalize missing quantity)
                    raw_inv = state.get('inventory', [])
                    normalized_inv = []
                    for entry in raw_inv:
                        if isinstance(entry, dict) and 'item_id' in entry and 'quantity' not in entry:
                            entry = dict(entry)
                            entry['quantity'] = 1
                        normalized_inv.append(entry)
                    st.inventory_engine._inventories[pid] = normalized_inv
                    result = handle_learn(state, resource_name, pid, recipe_manager, st.inventory_engine)
                    # Sync inventory changes (recipe item consumed if present)
                    state['inventory'] = st.inventory_engine._inventories.get(pid, state.get('inventory', []))
                    if result and result.get('message') and sio:
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            if sid_pid == pid:
                                sio.emit('command_result', {'message': result['message']}, room=sid)
                                break

                elif action == 'craft' and args:
                    resource_name = ' '.join(args)
                    p_map = pos.get('map_id', 'village')
                    p_node = pos.get('node_id', 'village_center')
                    from commands.techniques.crafting.craft_cmd import handle_craft
                    from server.state import recipe_manager
                    # Load player inventory into the shared inventory engine
                    st.inventory_engine._inventories[pid] = state.get('inventory', [])
                    result = handle_craft(state, resource_name, p_map, p_node,
                                          st.resource_node_manager, st.inventory_engine, st.equipment_engine,
                                          st.disciplines_engine, recipe_manager, st.long_action_queue,
                                          None, pid, st.tick_number)
                    # Sync back any changes (items consumed/produced)
                    state['inventory'] = st.inventory_engine._inventories.get(pid, state.get('inventory', []))
                    if result and result.get('message') and sio:
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            if sid_pid == pid:
                                sio.emit('command_result', {'message': result['message']}, room=sid)
                                break

                elif action == 'attack' and args:
                    # Process attack using full CombatEngine
                    from server.routes.combat import process_attack_command
                    process_attack_command(pid, cmd)

                elif action == 'inspect' and args:
                    target_name = ' '.join(args)
                    p_map = pos.get('map_id', 'village')
                    p_node = pos.get('node_id', 'village_center')
                    from commands.core.inspect_cmd import handle_inspect
                    # Load player inventory into the shared inventory engine
                    st.inventory_engine._inventories[pid] = state.get('inventory', [])
                    result = handle_inspect(state, target_name, pid, st.WORLD_ENTITIES, st.corpses, st.inspect_state, st.inventory_engine)
                    # Sync inventory changes
                    state['inventory'] = st.inventory_engine._inventories.get(pid, state.get('inventory', []))
                    if result and result.get('message') and sio:
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            if sid_pid == pid:
                                sio.emit('command_result', {'message': result['message']}, room=sid)
                                # Send inspect window data if inspection is open
                                if result.get('inspect_open'):
                                    sio.emit('inspect_window', {
                                        'target': result.get('target'),
                                        'items': result.get('items', [])
                                    }, room=sid)
                                break

                elif action == 'take' and args:
                    item_name = ' '.join(args)
                    qty = int(args[-1]) if args[-1].isdigit() and len(args) > 1 else 1
                    from commands.core.inspect_cmd import handle_take
                    # Load player inventory into the shared inventory engine
                    st.inventory_engine._inventories[pid] = state.get('inventory', [])
                    result = handle_take(state, item_name, qty, pid, st.inspect_state, st.inventory_engine, st.corpses)
                    # Sync inventory changes
                    state['inventory'] = st.inventory_engine._inventories.get(pid, state.get('inventory', []))
                    if result and result.get('message') and sio:
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            if sid_pid == pid:
                                sio.emit('command_result', {'message': result['message']}, room=sid)
                                # Remove empty corpse
                                if result.get('corpse_empty'):
                                    corpse_id = result.get('corpse_id')
                                    #print(f"[INSPECT] Attempting to remove corpse: {corpse_id}")
                                    #print(f"[INSPECT] Corpses before removal: {list(st.corpses.keys())}")
                                    if corpse_id:
                                        # Remove from corpses dict
                                        if corpse_id in st.corpses:
                                            del st.corpses[corpse_id]
                                            #print(f"[INSPECT] ✓ Removed empty corpse {corpse_id}")
                                        # Remove from CREATURE_INSTANCES and ACTOR_POSITIONS
                                        if corpse_id in st.CREATURE_INSTANCES:
                                            del st.CREATURE_INSTANCES[corpse_id]
                                            #print(f"[INSPECT] ✓ Removed creature instance {corpse_id}")
                                        if corpse_id in st.ACTOR_POSITIONS:
                                            del st.ACTOR_POSITIONS[corpse_id]
                                            #print(f"[INSPECT] ✓ Removed creature position {corpse_id}")
                                        # Add to death times to prevent respawn
                                        st.creature_death_times[corpse_id] = st.tick_number
                                        #print(f"[INSPECT] Corpses after removal: {list(st.corpses.keys())}")
                                # Update inspect window if still open
                                if result.get('inspect_open'):
                                    sio.emit('inspect_window', {
                                        'target': result.get('target'),
                                        'items': result.get('items', [])
                                    }, room=sid)
                                else:
                                    # Close inspect window
                                    sio.emit('inspect_close', {}, room=sid)
                                break

                elif action == 'close':
                    from commands.core.inspect_cmd import handle_close
                    result = handle_close(state, pid, st.inspect_state)
                    if result and result.get('message') and sio:
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            if sid_pid == pid:
                                sio.emit('command_result', {'message': result['message']}, room=sid)
                                # Close inspect window
                                sio.emit('inspect_close', {}, room=sid)
                                break

                elif action == 'drink' and args:
                    item_name = ' '.join(args)
                    from commands.core.drink_cmd import handle_drink
                    result = handle_drink(state, item_name, pid)
                    if result and result.get('message') and sio:
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            if sid_pid == pid:
                                sio.emit('command_result', {'message': result['message']}, room=sid)
                                break


            # Resolve any 0-tick actions that were just queued by pending commands
            from server.routes.crafting import resolve_crafting_action
            instant_results = process_tick(st.long_action_queue, st.tick_number, resolve_crafting_action)
            for result in instant_results:
                if result and result.get('message') and sio:
                    actor_id = result.get('actor_id')
                    for sid, sid_pid in st.player_sessions.items():
                        sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                        if sid_pid == actor_id:
                            sio.emit('command_result', {'message': result['message']}, room=sid)
                            break
                if result and result.get('actor_id') and sio:
                    from server.routes.inventory import emit_inventory_update
                    actor_sid = None
                    for sid, sid_pid in st.player_sessions.items():
                        sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                        if sid_pid == result['actor_id']:
                            actor_sid = sid
                            break
                    if actor_sid:
                        emit_inventory_update(result['actor_id'], sid=actor_sid)

            # Process active buffs - decrement duration and remove expired
            for pid in list(st.player_states.keys()):
                state = st.player_states[pid]
                if not state.get('name'):
                    continue
                
                if 'active_buffs' in state:
                    expired_buffs = []
                    for buff_stat, buff_data in state['active_buffs'].items():
                        buff_data['duration_ticks'] -= 1
                        if buff_data['duration_ticks'] <= 0:
                            expired_buffs.append(buff_stat)
                    
                    # Remove expired buffs
                    for buff_stat in expired_buffs:
                        del state['active_buffs'][buff_stat]
                        # Notify player
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            if sid_pid == pid:
                                if sio:
                                    sio.emit('command_result', {
                                        'message': f"Your {buff_stat} boost has worn off."
                                    }, room=sid)
                                break
            
            # Save all player states periodically (only logged-in characters)
            for pid in st.player_states:
                state = st.player_states[pid]
            # Skip saving states without a real character name
                if not state.get('name'):
                    continue
                from server.state import save_player_state
                save_player_state(pid)

            # Clean up expired disconnected players (6 tick grace period = 2 minutes)
            for pid in list(st.player_states.keys()):
                state = st.player_states[pid]
                if state.get('_disconnected') and state.get('_disconnect_tick'):
                    ticks_ago = st.tick_number - state['_disconnect_tick']
                    if ticks_ago > 6:
                        # Grace period expired - fully remove player
                        #print(f"[TICK] Removing expired disconnected player {pid} (disconnected {ticks_ago} ticks ago)")
                        if pid in st.player_states:
                            del st.player_states[pid]
                        if pid in ACTOR_POSITIONS:
                            del ACTOR_POSITIONS[pid]
                        continue
            
            # Decay threat on all actors (-100 per tick)
            if hasattr(sio, 'combat_engine'):
                for actor_id in list(sio.combat_engine._threat.keys()):
                    sio.combat_engine.decay_threat(actor_id, decay_amount=100)
            
            # Clean up empty corpses after 30 ticks (10 minutes)
            for corpse_id, empty_tick in list(st.empty_corpse_times.items()):
                if st.tick_number - empty_tick > 30:
                    if corpse_id in st.corpses:
                        del st.corpses[corpse_id]
                        #print(f"[CORPSE] Cleaned up empty corpse {corpse_id}")
                    del st.empty_corpse_times[corpse_id]

            # Initialize creature AI if not already done
            if not hasattr(sio, 'creature_ai'):
                from engine.creature_ai import CreatureAI
                from engine.combat_techniques import CombatTechniqueEngine
                from engine.effects import EffectEngine
                from engine.long_action import ActionQueue
                from engine.combat import CombatEngine
                from engine.equipment import EquipmentEngine
                from server.state import technique_manager, WORLD_MAPS
                
                # Initialize combat engines if needed
                if not hasattr(sio, 'combat_engine'):
                    sio.combat_engine = CombatEngine()
                if not hasattr(sio, 'equipment_engine'):
                    sio.equipment_engine = EquipmentEngine()
                
                technique_engine = CombatTechniqueEngine(
                    sio.combat_engine,
                    technique_manager,
                    EffectEngine(),
                    ActionQueue()
                )
                
                sio.creature_ai = CreatureAI(
                    world_maps=WORLD_MAPS,
                    actor_positions=st.ACTOR_POSITIONS,
                    get_actors_at_position=st.get_actors_at_position,
                    get_npc_data=st.get_npc_data,
                    technique_engine=technique_engine,
                    combat_engine=sio.combat_engine
                )
                #print("[AI] Creature AI initialized")
            
            # Update actor positions based on schedule (every tick)
            current_hour = st.get_game_hour()
            for actor_id, actor_data in st.CREATURE_INSTANCES.items():
                # Skip schedule movement if max_distance is 0 (NPC stays put)
                if actor_data.get('max_distance', 3) == 0:
                    continue
                
                schedule = actor_data.get('schedule', [])
                if not schedule:
                    continue
                
                # Find current schedule position
                found_schedule = False
                for schedule_item in schedule:
                    from_hour = schedule_item.get('from', 0)
                    to_hour = schedule_item.get('to', 24)
                    node_id = schedule_item.get('node_id')
                    map_id = schedule_item.get('map_id')
                    
                    if not node_id or not map_id:
                        continue
                    
                    # Check if current hour matches this schedule item
                    if from_hour < to_hour:
                        in_schedule = from_hour <= current_hour < to_hour
                    else:
                        # Overnight schedule (e.g., 22:00 to 08:00)
                        in_schedule = current_hour >= from_hour or current_hour < to_hour
                    
                    if in_schedule:
                        found_schedule = True
                        # Update position if different
                        current_pos = st.ACTOR_POSITIONS.get(actor_id, {})
                        if current_pos.get('map_id') != map_id or current_pos.get('node_id') != node_id:
                            st.ACTOR_POSITIONS[actor_id] = {'map_id': map_id, 'node_id': node_id}
                            #print(f"[SCHEDULE] {actor_id} moved to {map_id}/{node_id} (hour {current_hour})")
                        break
                
                # If no schedule matched (off-duty), keep at first valid schedule position
                if not found_schedule:
                    if actor_id not in st.ACTOR_POSITIONS:
                        for sched_item in schedule:
                            sched_node = sched_item.get('node_id')
                            sched_map = sched_item.get('map_id')
                            if sched_node and sched_map:
                                st.ACTOR_POSITIONS[actor_id] = {'map_id': sched_map, 'node_id': sched_node}
                                #print(f"[SCHEDULE] {actor_id} placed at {sched_map}/{sched_node} (off-duty fallback)")
                                break
            
            creature_ai = sio.creature_ai
            #print(f"[AI] Updating {len(st.CREATURE_INSTANCES)} creatures: {list(st.CREATURE_INSTANCES.keys())}")
            for actor_id, actor_data in list(st.CREATURE_INSTANCES.items()):
                # Skip dead creatures
                if actor_id in st.creature_death_times:
                    #print(f"[AI] Skipping dead creature: {actor_id}")
                    continue
                #print(f"[AI] Processing: {actor_id}, state={creature_ai.get_state(actor_id)}")
                # Register creature if not already registered
                if actor_id not in creature_ai._ai_state:
                    max_dist = actor_data.get('max_distance', 3)
                    creature_ai.register_creature(actor_id, max_distance=max_dist)
                # Get current NPC data (may have been modified)
                npc_data = st.get_npc_data(actor_id) or actor_data
                # Update AI
                ai_result = creature_ai.update(actor_id, npc_data, st.tick_number, socketio=sio)
                # Emit any AI messages to nearby players
                if ai_result and ai_result.get('message') and sio:
                    actor_pos = st.ACTOR_POSITIONS.get(actor_id)
                    if actor_pos:
                        # Find players in same node
                        for sid, sid_pid in st.player_sessions.items():
                            sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                            p_state = st.player_states.get(sid_pid)
                            if not p_state:
                                continue
                            p_pos = p_state.get('position', {})
                            if p_pos.get('map_id') == actor_pos.get('map_id') and p_pos.get('node_id') == actor_pos.get('node_id'):
                                sio.emit('command_result', {'message': ai_result['message']}, room=sid)

            # Send world updates - only to players with active socket sessions
            for player_id, state in st.player_states.items():
                # Skip states without a real character name
                if not state.get('name'):
                    continue
                from server.routes.world import build_world_update_for_state
                update = build_world_update_for_state(player_id, state)
                # Send to ALL active sessions for this player (handles reconnection edge cases
                # where duplicate sessions may temporarily exist)
                has_active_session = False
                for sid, sid_pid in st.player_sessions.items():
                    sid_pid = sid_pid.get('player_id') if isinstance(sid_pid, dict) else sid_pid
                    if sid_pid == player_id:
                        if sio:
                            sio.emit('world_update', update, room=sid)
                            has_active_session = True
                if not has_active_session:
                    continue

            # Send tick update
            if sio:
                sio.emit('tick_update', {
                    'tick': st.tick_number,
                    'time': st.get_game_time(),
                    'time_of_day': st.get_time_of_day()
                })

    tick_thread = threading.Thread(target=tick_loop, daemon=True)
    tick_thread.start()
    #print("[TICK] Tick loop started")