"""
Attack Command (Phase 6F)

Implements the basic attack command:
  attack <target>

Uses existing systems:
- Combat Engine
- Long Actions
- Action Resolution
- Equipment
- Effects
- Engagement Graph

No techniques. No magic. No special attacks.
"""

from typing import Optional, Dict, Any

# Import combat events
from engine.combat import (
    EVENT_ATTACK_STARTED,
    EVENT_ATTACK_HIT,
    EVENT_ATTACK_MISSED,
    EVENT_ACTOR_DOWNED,
    EVENT_ACTOR_DIED,
)


# ============ ATTACK COMMAND ============


def create_attack_command(
    actor_id: str,
    target_id: str,
    combat_engine,
    action_queue,
    equipment_engine=None,
    current_tick: int = 0,
) -> Dict[str, Any]:
    """Create an attack command.

    Args:
        actor_id: Attacking actor
        target_id: Target actor
        combat_engine: Combat engine instance
        equipment_engine: Equipment engine instance (optional)
        current_tick: Current world tick

    Returns:
        Command result dict
    """
    # Validate actors
    if not combat_engine.has_actor(actor_id):
        return {"success": False, "message": f"Unknown actor: {actor_id}"}

    if not combat_engine.has_actor(target_id):
        return {"success": False, "message": f"Unknown target: {target_id}"}

    # Check if actor is downed
    actor_hp = combat_engine.get_hp(actor_id)
    if actor_hp["current"] <= 0:
        return {"success": False, "message": "You are downed and cannot attack."}

    # Check if target is downed
    target_hp = combat_engine.get_hp(target_id)
    if target_hp["current"] <= 0:
        return {"success": False, "message": "Target is already downed."}

    # Check if actor is stunned
    if combat_engine.has_effect(actor_id, "stunned"):
        return {"success": False, "message": "You are stunned and cannot attack."}

    # Get attack profile
    from engine.combat import get_weapon_attack_profile
    profile = get_weapon_attack_profile(equipment_engine, actor_id) if equipment_engine else None

    # Create long action (1 tick)
    from engine.long_action import STATUS_QUEUED

    # Build resolution config using constructed_attribute from profile
    if profile and "constructed_attribute" in profile:
        # New format: use constructed_attribute
        resolution_config = {
            "constructed_attribute": profile["constructed_attribute"],
            "target_attribute": "observation",
        }
    else:
        # Legacy format: use primary_attribute
        resolution_config = {
            "actor_attribute": profile["primary_attribute"] if profile else "strength",
            "target_attribute": "observation",
        }

    action = action_queue.queue_action(
        actor_id=actor_id,
        action_type="attack",
        duration_ticks=1,
        current_tick=current_tick,
        target={"id": target_id},
        parameters={
            "profile_id": profile["id"] if profile else "unarmed",
            "profile_name": profile["name"] if profile else "Unarmed Attack",
        },
        resolution_config=resolution_config,
    )

    if not action:
        return {"success": False, "message": "Actor already has an active action."}

    # Generate event
    combat_engine._generate_event(
        EVENT_ATTACK_STARTED,
        actor_id,
        current_tick,
        target_id=target_id,
        data={"profile": profile["id"] if profile else "unarmed"},
    )

    return {
        "success": True,
        "message": f"{actor_id} attacks {target_id} with {profile['name'] if profile else 'Unarmed Attack'}!",
        "action_id": action["action_id"],
        "profile": profile["id"] if profile else "unarmed",
        "duration": 1,
    }


def resolve_attack_command(
    action_id: str,
    combat_engine,
    action_queue,
    equipment_engine=None,
    current_tick: int = 0,
) -> Dict[str, Any]:
    """Resolve an attack command after long action completes.

    Args:
        action_id: Action ID to resolve
        combat_engine: Combat engine instance
        equipment_engine: Equipment engine instance (optional)
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
    params = action["parameters"]

    # Use provided attacker_data and target_data from action if available
    # Otherwise fall back to combat engine (which may have placeholder data)
    actor_data = action.get("attacker_data") or combat_engine.get_actor_data(actor_id)
    target_data = action.get("target_data") or combat_engine.get_actor_data(target_id)

    if not actor_data or not target_data:
        return {"success": False, "message": "Actor or target data not found."}

    # Use combat engine's attack method
    result = combat_engine.attack(
        attacker_id=actor_id,
        target_id=target_id,
        equipment_engine=equipment_engine,
        current_tick=current_tick,
        attacker_data=actor_data,
        target_data=target_data,
        action_config=action["resolution_config"],
    )

    if not result["success"]:
        return {
            "success": False,
            "message": result["message"],
        }

    # Build response
    blocked = result.get("damage", {}).get("shield_absorption", 0) > 0
    profile_name = params.get("profile_name", "Unarmed Attack")

    msg = f"{actor_id} attacks {target_id} with {profile_name}!"
    if "damage" in result:
        damage_result = result["damage"]
        damage_type = damage_result.get("damage_type", "bludgeoning")
        if blocked:
            msg += f" Blocked! {damage_result['hp_damage']} damage gets through."
        else:
            msg += f" {damage_result['hp_damage']} {damage_type} damage!"

    return {
        "success": True,
        "hit": result["hit"],
        "damage": result.get("damage", {}).get("hp_damage", 0),
        "blocked": blocked,
        "message": msg,
        "damage_calculation": result.get("damage", {}),
        "target_hp": result.get("target_hp", {}),
    }


