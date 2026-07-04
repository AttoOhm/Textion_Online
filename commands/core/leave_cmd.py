"""
Leave Group Command (Phase 6G)

Implements the leave group command:
  leave group

Creates a 1-tick long action.
On completion, actor removes all engagement links involving themselves.

Uses existing systems:
- Long Actions
- Engagement Graph
- Combat Engine

No new damage systems.
No new techniques.
No magic.
"""

from typing import Optional, Dict, Any


# ============ LEAVE GROUP COMMAND ============


def create_leave_group_command(
    actor_id: str,
    combat_engine,
    action_queue,
    current_tick: int = 0,
) -> Dict[str, Any]:
    """Create a leave group command.

    Args:
        actor_id: Actor leaving the group
        combat_engine: Combat engine instance
        action_queue: Action queue instance
        current_tick: Current world tick

    Returns:
        Command result dict
    """
    # Validate actor exists
    if not combat_engine.has_actor(actor_id):
        return {"success": False, "message": f"Unknown actor: {actor_id}"}

    # Check if actor is downed
    actor_hp = combat_engine.get_hp(actor_id)
    if actor_hp["current"] <= 0:
        return {"success": False, "message": "You are downed and cannot leave group."}

    # Create long action (1 tick)
    from engine.long_action import STATUS_QUEUED

    action = action_queue.queue_action(
        actor_id=actor_id,
        action_type="leave_group",
        duration_ticks=1,
        current_tick=current_tick,
        target=None,
        parameters={},
        resolution_config={},
    )

    if not action:
        return {"success": False, "message": "Actor already has an active action."}

    return {
        "success": True,
        "message": f"{actor_id} prepares to leave the combat group...",
        "action_id": action["action_id"],
        "duration": 1,
    }


def resolve_leave_group_command(
    action_id: str,
    combat_engine,
    action_queue,
    current_tick: int = 0,
) -> Dict[str, Any]:
    """Resolve a leave group command after long action completes.

    Args:
        action_id: Action ID to resolve
        combat_engine: Combat engine instance
        action_queue: Action queue instance
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
    target_id = action["target"]["id"]  # The actor we're leaving from

    # Get engagement graph
    engagement = combat_engine.get_engagement()

    # Check if actor is actually linked to target
    if not engagement.has_link(actor_id, target_id):
        return {
            "success": False,
            "message": f"{actor_id} is not engaged with {target_id}.",
            "left_group": False,
        }

    # Check for leave interception (attack pressure)
    # If target attacked actor during the leave action, opposed resolution occurs
    attack_pressure = combat_engine._attack_pressure.get(actor_id, 0)
    
    # Use proper opposed resolution for leave interception
    # Actor: Reactiveness vs Target: Reactiveness + Attack Pressure
    if attack_pressure > 0:
        from engine.action_resolution import resolve_opposed_action, OUTCOME_SUCCESS, OUTCOME_EXCEPTIONAL_SUCCESS
        
        actor_data = combat_engine.get_actor_data(actor_id)
        target_data = combat_engine.get_actor_data(target_id)
        
        if actor_data and target_data:
            # Actor uses reactiveness to escape
            actor_action_def = {"constructed_attribute": {"reactiveness": 1.0}}
            
            # Target uses reactiveness + attack pressure to hold
            target_action_def = {
                "constructed_attribute": {"reactiveness": 1.0},
                "modifiers": [attack_pressure],  # Each attack adds +1 to target
            }
            
            result = resolve_opposed_action(
                actor=actor_data,
                target=target_data,
                actor_attribute_name="reactiveness",
                target_attribute_name="reactiveness",
                actor_action_definition=actor_action_def,
                target_action_definition=target_action_def,
            )
            
            leave_succeeds = result["outcome"] in (OUTCOME_SUCCESS, OUTCOME_EXCEPTIONAL_SUCCESS)
            
            if not leave_succeeds:
                # Leave failed - intercepted
                combat_engine._generate_event(
                    combat_engine.EVENT_GROUP_LEFT,
                    actor_id,
                    current_tick,
                    target_id=target_id,
                    data={
                        "intercepted": True,
                        "attack_pressure": attack_pressure,
                        "margin": result["margin"],
                        "outcome": result["outcome"],
                    },
                )
                
                return {
                    "success": True,
                    "message": f"{actor_id} fails to leave {target_id}'s group! (Intercepted)",
                    "left_group": False,
                    "intercepted": True,
                    "margin": result["margin"],
                    "outcome": result["outcome"],
                }

    # Remove only the specific link to target
    engagement.remove_link(actor_id, target_id)

    # Generate event
    combat_engine._generate_event(
        combat_engine.EVENT_GROUP_LEFT,
        actor_id,
        current_tick,
        target_id=target_id,
        data={"left_from": target_id, "intercepted": False},
    )

    return {
        "success": True,
        "message": f"{actor_id} leaves {target_id}'s group.",
        "left_group": True,
        "target_id": target_id,
        "intercepted": False,
    }
