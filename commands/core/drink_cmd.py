"""
Drink Command (Phase 8C)

Short command: drink <item>
Consume consumable items (potions, food, etc.).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def handle_drink(player_state, item_name, actor_id, combat_engine=None):
    """Handle the 'drink <item>' command."""
    item_name_lower = item_name.lower().replace(" ", "_")
    
    # Check inventory
    inventory = player_state.get('inventory', [])
    item_index = None
    item_entry = None
    
    for i, inv_item in enumerate(inventory):
        if isinstance(inv_item, dict):
            item_id = inv_item.get('item_id', '').lower()
            item_display = inv_item.get('name', '').lower()
            if item_id == item_name_lower or item_name_lower in item_id or item_name_lower in item_display:
                item_index = i
                item_entry = inv_item
                break
        elif isinstance(inv_item, str):
            if inv_item.lower() == item_name_lower or item_name_lower in inv_item.lower():
                item_index = i
                item_entry = {'item_id': inv_item.lower().replace(' ', '_'), 'name': inv_item}
                break
    
    if item_index is None:
        return {"success": False, "message": f"You don't have '{item_name}' in your inventory."}
    
    # Get item data
    from engine.items import get_item_definition
    item_id = item_entry.get('item_id', item_name_lower)
    item_def = get_item_definition(item_id)
    
    if not item_def:
        return {"success": False, "message": f"Unknown item: '{item_name}'."}
    
    # Check if consumable
    if not item_def.get('consumable', False):
        return {"success": False, "message": f"You cannot drink '{item_name}'. It's not consumable."}
    
    # Apply effects
    message_parts = [f"You drink {item_def.get('name', item_name)}."]
    
    # Healing effect
    heal_amount = item_def.get('heal_amount', 0)
    if heal_amount > 0:
        current_hp = player_state.get('hp', 0)
        max_hp = player_state.get('max_hp', 100)
        
        if current_hp >= max_hp:
            message_parts.append("You are already at full health.")
        else:
            new_hp = min(max_hp, current_hp + heal_amount)
            player_state['hp'] = new_hp
            healed = new_hp - current_hp
            message_parts.append(f"You restore {healed} HP.")
    
    # Mana restoration
    mana_restore = item_def.get('mana_restore', 0)
    if mana_restore > 0:
        current_mana = player_state.get('mana', 0)
        max_mana = player_state.get('max_mana', 50)
        
        if current_mana >= max_mana:
            message_parts.append("You are already at full mana.")
        else:
            new_mana = min(max_mana, current_mana + mana_restore)
            player_state['mana'] = new_mana
            restored = new_mana - current_mana
            message_parts.append(f"You restore {restored} mana.")
    
    # Buff effects
    buff = item_def.get('buff')
    if buff:
        stat = buff.get('stat')
        amount = buff.get('amount', 0)
        duration = buff.get('duration', 30)
        
        if stat and amount > 0:
            # Initialize buffs tracking if not present
            if 'active_buffs' not in player_state:
                player_state['active_buffs'] = {}
            
            # Apply buff
            player_state['active_buffs'][stat] = {
                'amount': amount,
                'duration_ticks': duration,
                'source': item_name
            }
            
            message_parts.append(f"Your {stat} increases by {amount} for {duration} seconds!")
    
    # Remove item
    inventory.pop(item_index)
    player_state['inventory'] = inventory
    
    return {"success": True, "message": " ".join(message_parts)}
