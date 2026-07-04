"""
Join Group Command (Phase 6G)

Implements the join group command:
  join <actor>

Creates a 1-tick long action.
On completion, actor enters target's combat group by creating engagement link.

Uses existing systems:
- Long Actions
- Engagement Graph
- Combat Engine

No new damage systems.
No new techniques.
No magic.
"""

from typing import Optional, Dict, Any


# ============ JOIN GROUP COMMAND ============


def create_join_group_command(
    actor_id: str,
    target_id: str,
    combat_engine,
    action_queue,
    current_tick: int = 0,
) -> Dict[str, Any]:
    """Create a join group command.

    Args:
        actor_id: Actor joining the group
        target_id: Target actor to join
        combat_engine: Combat engine instance
        action_queue: Action queue instance
        current_tick: Current world tick

    Returns:
        Command result dict
    """
    # Validate actors exist
    if not combat_engine.has_actor(actor_id):
        return {"success": False, "message": f"Unknown actor: {actor_id}"}

    if not combat_engine.has_actor(target_id):
        return {"success": False, "message": f"Unknown target: {target_id}"}

    # Check if actor is downed
    actor_hp = combat_engine.get_hp(actor_id)
    if actor_hp["current"] <= 0:
        return {"success": False, "message": "You are downed and cannot join group."}

    # Check if already in same group
    if combat_engine.is_same_combat_group(actor_id, target_id):
        return {"success": False, "message": f"You are already in the same combat group as {target_id}."}

    # Create long action (1 tick)
    from engine.long_action import STATUS_QUEUED

    action = action_queue.queue_action(
        actor_id=actor_id,
        action_type="join_group",
        duration_ticks=1,
        current_tick=current_tick,
        target={"id": target_id},
        parameters={"target_id": target_id},
        resolution_config={},
    )

    if not action:
        return {"success": False, "message": "Actor already has an active action."}

    return {
        "success": True,
        "message": f"{actor_id} prepares to join {target_id}'s combat group...",
        "action_id": action["action_id"],
        "duration": 1,
    }


def resolve_join_group_command(
    action_id: str,
    combat_engine,
    action_queue,
    current_tick: int = 0,
) -> Dict[str, Any]:
    """Resolve a join group command after long action completes.

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
    target_id = action["target"]["id"]

    # Get engagement graph
    engagement = combat_engine.get_engagement()

    # Check if already linked (shouldn't happen, but safety check)
    if engagement.has_link(actor_id, target_id):
        return {
            "success": True,
            "message": f"{actor_id} is already in {target_id}'s combat group.",
            "joined_group": False,
        }

    # Create engagement link
    engagement.add_link(actor_id, target_id)

    # Generate event
    combat_engine._generate_event(
        combat_engine.EVENT_GROUP_JOINED,
        actor_id,
        current_tick,
        target_id=target_id,
        data={"joined_group_of": target_id},
    )

    return {
        "success": True,
        "message": f"{actor_id} joins {target_id}'s combat group.",
        "joined_group": True,
        "target_id": target_id,
    }