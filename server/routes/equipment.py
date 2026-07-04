"""
Equipment routes - equip/unequip commands.
"""

from flask import request
from flask_socketio import emit
from server.state import (
    socketio, player_sessions, player_states
)
from server.state import get_player_state, _items_db


@socketio.on('command')
def handle_command(command):
    """Handle equipment commands."""
    sid = request.sid
    player_id = player_sessions.get(sid, 'default_player')
    state = get_player_state(player_id)
    cmd = command.strip().lower()
    cmd_parts = cmd.split()
    base_cmd = cmd_parts[0] if cmd_parts else ''
    
    if base_cmd == 'equip' and len(cmd_parts) > 1:
        # Equip an item from inventory
        item_name = ' '.join(cmd_parts[1:]).lower()
        inventory = state.get('inventory', [])
        
        # Find item in inventory
        item_index = None
        for i, inv_item in enumerate(inventory):
            if isinstance(inv_item, str) and inv_item.lower() == item_name:
                item_index = i
                break
            elif isinstance(inv_item, dict) and inv_item.get('name', '').lower() == item_name:
                item_index = i
                break
        
        if item_index is None:
            emit('command_result', {'error': f"You don't have {item_name} in your inventory."})
        else:
            # Get item data
            item_data = _items_db.get(item_name)
            if not item_data:
                inv_item = inventory[item_index]
                if isinstance(inv_item, dict):
                    item_data = inv_item
                else:
                    item_data = {'id': item_name, 'name': item_name}
            
            # Determine equipment slot
            category = item_data.get('category', '').lower()
            subtype = item_data.get('subtype', '').lower()
            
            equipment = state.setdefault('equipment', {})
            slot = None
            
            if category == 'weapon' or subtype in ['sword', 'dagger', 'axe', 'hammer', 'bow', 'staff', 'wand']:
                slot = 'main_hand'
            elif category == 'armor':
                slot = 'armor'
            elif category == 'container' and subtype == 'quiver':
                slot = 'off_hand'
            
            # Fail-safe slot detection
            if not slot:
                if any(kw in item_name for kw in ['sword', 'dagger', 'axe', 'hammer', 'bow', 'staff', 'wand']):
                    slot = 'main_hand'
                elif any(kw in item_name for kw in ['hatchet', 'pickaxe', 'sickle', 'tool']):
                    slot = 'main_hand'
                elif any(kw in item_name for kw in ['shield', 'buckler']):
                    slot = 'off_hand'
                elif any(kw in item_name for kw in ['armor', 'robe', 'tunic', 'cuirass']):
                    slot = 'armor'
            
            if not slot:
                emit('command_result', {'error': f"You cannot equip {item_name}."})
            else:
                # Remove from inventory
                inventory.pop(item_index)
                
                # Unequip current item in that slot if any
                current_equipped = equipment.get(slot)
                if current_equipped:
                    inventory.append(current_equipped)
                
                # Look up canonical item_id
                db_item = _items_db.get(item_name)
                if not db_item:
                    for key, itm in _items_db.items():
                        if isinstance(itm, dict) and itm.get('name', '').lower() == item_name:
                            db_item = itm
                            break
                canonical_id = db_item.get('id', item_name) if db_item else item_name
                display_name = db_item.get('name', item_name.title()) if db_item else item_name.title()
                
                # Equip new item
                equipment[slot] = {"item_id": canonical_id, "name": display_name}
                
                emit('command_result', {'message': f"You equip {item_name.title()}."})
    
    elif base_cmd == 'unequip' and len(cmd_parts) > 1:
        # Unequip an item or slot
        target = ' '.join(cmd_parts[1:]).lower()
        equipment = state.setdefault('equipment', {})
        inventory = state.setdefault('inventory', [])
        
        # Check if target is a slot name
        slot_key = target.replace(' ', '_')
        if slot_key in equipment:
            item_entry = equipment.get(slot_key)
            if item_entry:
                item_name = item_entry.get('name', item_entry.get('item_id', str(item_entry)))
                inventory.append(item_name)
                equipment[slot_key] = None
                emit('command_result', {'message': f"You unequip {item_name} from your {target}."})
            else:
                emit('command_result', {'error': f"Nothing is equipped in your {target}."})
        else:
            # Check if it's an item name in one of the slots
            found_slot = None
            for slot, item in equipment.items():
                if item:
                    item_name = item.get('name', item.get('item_id', str(item))).lower()
                    if item_name == target:
                        found_slot = slot
                        break
            
            if found_slot:
                item_entry = equipment[found_slot]
                item_name = item_entry.get('name', item_entry.get('item_id', str(item_entry)))
                inventory.append(item_name)
                equipment[found_slot] = None
                emit('command_result', {'message': f"You unequip {item_name}."})
            else:
                emit('command_result', {'error': f"{target.title()} is not equipped."})