"""
Reload Quiver Command (Phase 6G.3)

Implements the reload quiver command:
  reload quiver
  reload quiver with iron arrow
  reload quiver with fire arrow

1-tick bonus action.
Transfers arrows from inventory into quiver.
Only one arrow type per quiver at a time.

Uses existing systems:
- Long Actions
- Equipment
- Inventory (implicit)

No new damage systems.
No new techniques.
No magic.
"""

from typing import Optional, Dict, Any


# ============ RELOAD QUIVER COMMAND ============


def create_reload_quiver_command(
    actor_id: str,
    arrow_item_id: Optional[str],
    equipment_engine,
    action_queue,
    current_tick: int = 0,
) -> Dict[str, Any]:
    """Create a reload quiver command.

    Args:
        actor_id: Actor reloading quiver
        arrow_item_id: Item ID of arrow to load (None for auto-detect)
        equipment_engine: Equipment engine instance
        action_queue: Action queue instance
        current_tick: Current world tick

    Returns:
        Command result dict
    """
    # Validate actor exists
    if not equipment_engine.has_actor(actor_id):
        return {"success": False, "message": f"Unknown actor: {actor_id}"}

    # Check if actor has quiver equipped in off_hand
    quiver = equipment_engine.get_equipped_item(actor_id, "off_hand")
    if not quiver:
        return {"success": False, "message": f"{actor_id} does not have a quiver equipped!"}

    # Validate quiver is actually a quiver
    from engine.items import get_item_definition
    quiver_id = quiver.get("item_id", "")
    quiver_def = get_item_definition(quiver_id)
    if not quiver_def or quiver_def.get("subtype") != "quiver":
        return {"success": False, "message": f"{actor_id} does not have a quiver equipped!"}

    # Get quiver capacity
    quiver_capacity = quiver_def.get("capacity", 0)
    current_quantity = quiver.get("quantity", 0)

    # Check if quiver is full
    if current_quantity >= quiver_capacity:
        return {"success": False, "message": f"{actor_id}'s quiver is already full!"}

    # If no arrow specified, try to find arrows in inventory
    if not arrow_item_id:
        # TODO: Search inventory for arrows
        # For now, require explicit arrow item ID
        return {
            "success": False,
            "message": "Please specify which arrow to load: reload quiver with <arrow_item_id>",
        }

    # Validate arrow item
    arrow_def = get_item_definition(arrow_item_id)
    if not arrow_def or arrow_def.get("subtype") != "arrow":
        return {"success": False, "message": f"{arrow_item_id} is not a valid arrow!"}

    # Check if quiver already has different arrow type
    if current_quantity > 0:
        # Get current arrow type from quiver
        # For now, assume quiver stores the arrow item_id
        current_arrow_id = quiver.get("arrow_item_id")
        if current_arrow_id and current_arrow_id != arrow_item_id:
            return {
                "success": False,
                "message": f"Quiver already contains different arrows. Empty it first!",
            }

    # Create long action (1 tick)
    from engine.long_action import STATUS_QUEUED

    action = action_queue.queue_action(
        actor_id=actor_id,
        action_type="reload_quiver",
        duration_ticks=1,
        current_tick=current_tick,
        target=None,
        parameters={
            "arrow_item_id": arrow_item_id,
        },
        resolution_config={},
    )

    if not action:
        return {"success": False, "message": "Actor already has an active action."}

    return {
        "success": True,
        "message": f"{actor_id} prepares to reload quiver with {arrow_item_id}...",
        "action_id": action["action_id"],
        "duration": 1,
    }


def resolve_reload_quiver_command(
    action_id: str,
    equipment_engine,
    action_queue,
    inventory_engine=None,
    current_tick: int = 0,
) -> Dict[str, Any]:
    """Resolve a reload quiver command after long action completes.

    Args:
        action_id: Action ID to resolve
        equipment_engine: Equipment engine instance
        action_queue: Action queue instance
        inventory_engine: Inventory engine instance (required for actual reload)
        current_tick: Current world tick

    Returns:
        Resolution result dict
    """
    # Get action from queue
    action = action_queue.get_all_actions()
    action = next((a for a in action if a["action_id"] == action_id), None)
    if not action:
        return {"success": False, "message": "Action not found."}

    if action["status"] != "completed":
        return {"success": False, "message": "Action not completed."}

    actor_id = action["actor_id"]
    params = action["parameters"]
    arrow_item_id = params.get("arrow_item_id")

    # Get quiver from off_hand (container system)
    quiver = equipment_engine.get_equipped_item(actor_id, "off_hand")
    if not quiver:
        return {"success": False, "message": f"{actor_id} does not have a quiver equipped!"}

    # Verify it's a quiver
    from engine.items import get_item_definition
    quiver_id = quiver.get("item_id", "")
    quiver_def = get_item_definition(quiver_id)
    if not quiver_def or quiver_def.get("subtype") != "quiver":
        return {"success": False, "message": f"{actor_id} does not have a quiver equipped!"}

    # Get quiver capacity
    quiver_capacity = quiver_def.get("capacity", 0)
    current_quantity = quiver.get("quantity", 0)

    # Calculate how many arrows to add
    space_available = quiver_capacity - current_quantity
    if space_available <= 0:
        return {"success": True, "message": f"{actor_id}'s quiver is already full!", "reloaded": False}

    # Require inventory engine for actual reload
    if not inventory_engine:
        return {"success": False, "message": "Inventory engine required for reload!"}

    # Get arrows from inventory
    arrows_in_inventory = inventory_engine.get_item_quantity(actor_id, arrow_item_id)
    if arrows_in_inventory <= 0:
        return {"success": False, "message": f"{actor_id} has no {arrow_item_id} in inventory!"}

    # Calculate how many arrows to transfer
    arrows_to_add = min(space_available, arrows_in_inventory)

    # Remove arrows from inventory
    for _ in range(arrows_to_add):
        inventory_engine.remove_item(actor_id, arrow_item_id)

    # Update quiver
    quiver["quantity"] = current_quantity + arrows_to_add
    quiver["arrow_item_id"] = arrow_item_id

    return {
        "success": True,
        "message": f"{actor_id} reloads quiver with {arrow_item_id} (+{arrows_to_add} arrows).",
        "reloaded": True,
        "arrows_added": arrows_to_add,
        "total_arrows": quiver["quantity"],
    }
