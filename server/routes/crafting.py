"""
Crafting routes - craft command and long action resolution.
"""

from flask import request
from flask_socketio import emit
from server.state import (
    socketio, player_sessions, player_states
)
from server.state import get_player_state, pending_commands, familiarity_engine


@socketio.on('command')
def handle_command(command):
    """Handle crafting commands."""
    sid = request.sid
    player_id = player_sessions.get(sid, 'default_player')
    cmd = command.strip().lower()
    cmd_parts = cmd.split()
    base_cmd = cmd_parts[0] if cmd_parts else ''
    
    if base_cmd in ['craft', 'chop', 'mine', 'harvest', 'smelt', 'repair', 'saw', 'grind', 'learn']:
        # Queue crafting command for tick processing
        if player_id not in pending_commands:
            pending_commands[player_id] = []
        pending_commands[player_id].append(command)
        emit('command_result', {'message': f'[{command}] queued.'})


def resolve_crafting_action(action, current_tick):
    """Resolve completed crafting/gathering actions."""
    from server.state import player_states, long_action_queue
    from engine.inventory import InventoryEngine
    from engine.items import is_stackable
    
    action_type = action.get('action_type')
    actor_id = action.get('actor_id')
    params = action.get('parameters', {})
    
    player_state = get_player_state(actor_id)
    if not player_state:
        return None
    
    if 'inventory' not in player_state:
        player_state['inventory'] = []
    
    result_message = None
    
    if action_type == 'chop':
        from commands.techniques.crafting.chop_cmd import complete_chop
        from server.state import resource_node_manager
        inv_engine = InventoryEngine()
        normalized = []
        for entry in player_state['inventory']:
            if isinstance(entry, str):
                normalized.append({"item_id": entry, "quantity": 1})
            elif isinstance(entry, dict) and "item_id" in entry:
                normalized.append(entry)
            else:
                normalized.append(entry)
        inv_engine._inventories[actor_id] = normalized
        result = complete_chop(action, resource_node_manager, inv_engine, None, current_tick)
        player_state['inventory'] = inv_engine._inventories.get(actor_id, player_state['inventory'])
        if result and result.get('message'):
            result_message = result['message']
    
    elif action_type == 'mine':
        from commands.techniques.crafting.mine_cmd import complete_mine
        from server.state import resource_node_manager
        inv_engine = InventoryEngine()
        normalized = []
        for entry in player_state['inventory']:
            if isinstance(entry, str):
                normalized.append({"item_id": entry, "quantity": 1})
            elif isinstance(entry, dict) and "item_id" in entry:
                normalized.append(entry)
            else:
                normalized.append(entry)
        inv_engine._inventories[actor_id] = normalized
        result = complete_mine(action, resource_node_manager, inv_engine, None, current_tick)
        player_state['inventory'] = inv_engine._inventories.get(actor_id, player_state['inventory'])
        if result and result.get('message'):
            result_message = result['message']
    
    elif action_type == 'harvest':
        from commands.techniques.crafting.harvest_cmd import complete_harvest
        from server.state import resource_node_manager
        inv_engine = InventoryEngine()
        inv_engine._inventories[actor_id] = player_state['inventory']
        result = complete_harvest(action, resource_node_manager, inv_engine, None, current_tick)
        player_state['inventory'] = inv_engine._inventories.get(actor_id, player_state['inventory'])
        if result and result.get('message'):
            result_message = result['message']

    elif action_type == 'saw':
        from commands.techniques.crafting.saw_cmd import complete_saw
        inv_engine = InventoryEngine()
        normalized = []
        for entry in player_state['inventory']:
            if isinstance(entry, str):
                normalized.append({"item_id": entry, "quantity": 1})
            elif isinstance(entry, dict) and "item_id" in entry:
                normalized.append(entry)
            else:
                normalized.append(entry)
        inv_engine._inventories[actor_id] = normalized
        result = complete_saw(action, inv_engine, current_tick)
        player_state['inventory'] = inv_engine._inventories.get(actor_id, player_state['inventory'])
        if result and result.get('message'):
            result_message = result['message']

    elif action_type == 'smelt':
        from commands.techniques.crafting.smelt_cmd import complete_smelt
        inv_engine = InventoryEngine()
        normalized = []
        for entry in player_state['inventory']:
            if isinstance(entry, str):
                normalized.append({"item_id": entry, "quantity": 1})
            elif isinstance(entry, dict) and "item_id" in entry:
                normalized.append(entry)
            else:
                normalized.append(entry)
        inv_engine._inventories[actor_id] = normalized
        result = complete_smelt(action, inv_engine, current_tick)
        player_state['inventory'] = inv_engine._inventories.get(actor_id, player_state['inventory'])
        if result and result.get('message'):
            result_message = result['message']

    elif action_type == 'grind':
        from commands.techniques.crafting.grind_cmd import complete_grind
        inv_engine = InventoryEngine()
        normalized = []
        for entry in player_state['inventory']:
            if isinstance(entry, str):
                normalized.append({"item_id": entry, "quantity": 1})
            elif isinstance(entry, dict) and "item_id" in entry:
                normalized.append(entry)
            else:
                normalized.append(entry)
        inv_engine._inventories[actor_id] = normalized
        result = complete_grind(action, None, inv_engine, None, current_tick)
        player_state['inventory'] = inv_engine._inventories.get(actor_id, player_state['inventory'])
        if result and result.get('message'):
            result_message = result['message']

    elif action_type == 'repair':
        from commands.techniques.crafting.repair_cmd import complete_repair
        inv_engine = InventoryEngine()
        normalized = []
        for entry in player_state['inventory']:
            if isinstance(entry, str):
                normalized.append({"item_id": entry, "quantity": 1})
            elif isinstance(entry, dict) and "item_id" in entry:
                normalized.append(entry)
            else:
                normalized.append(entry)
        inv_engine._inventories[actor_id] = normalized
        result = complete_repair(action, None, inv_engine, None, current_tick)
        player_state['inventory'] = inv_engine._inventories.get(actor_id, player_state['inventory'])
        if result and result.get('message'):
            result_message = result['message']

    elif action_type == 'craft':
        from commands.techniques.crafting.craft_cmd import complete_craft
        inv_engine = InventoryEngine()
        normalized = []
        for entry in player_state['inventory']:
            if isinstance(entry, str):
                normalized.append({"item_id": entry, "quantity": 1})
            elif isinstance(entry, dict) and "item_id" in entry:
                normalized.append(entry)
            else:
                normalized.append(entry)
        inv_engine._inventories[actor_id] = normalized
        result = complete_craft(action, inv_engine, familiarity_engine, current_tick, player_state)
        player_state['inventory'] = inv_engine._inventories.get(actor_id, player_state['inventory'])
        if result and result.get('message'):
            result_message = result['message']
    
    return {'actor_id': actor_id, 'message': result_message}
