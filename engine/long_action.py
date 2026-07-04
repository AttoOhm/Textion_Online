"""
Long Action Framework (Phase 4C)

Implements the long action system that all future gameplay systems will use.
This is infrastructure only. No gameplay systems are implemented.

Key Properties:
- One active long action per actor (default)
- Actions progress over ticks
- Actions resolve when end_tick is reached
- Events are generated for action lifecycle
- Uses existing Action Resolution Engine

Statuses:
- queued: Action is waiting to start
- active: Action is in progress
- completed: Action has finished successfully
- cancelled: Action was cancelled
- failed: Action failed
"""

import uuid
import time
from typing import Optional, Dict, List, Any, Callable

# ============ CONSTANTS ============

STATUS_QUEUED = "queued"
STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"
STATUS_FAILED = "failed"

VALID_STATUSES = [
    STATUS_QUEUED,
    STATUS_ACTIVE,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    STATUS_FAILED,
]

EVENT_ACTION_STARTED = "action_started"
EVENT_ACTION_COMPLETED = "action_completed"
EVENT_ACTION_CANCELLED = "action_cancelled"
EVENT_ACTION_FAILED = "action_failed"

DEFAULT_DURATION_TICKS = 1


# ============ LONG ACTION SCHEMA ============


def create_long_action(
    action_id: Optional[str] = None,
    action_type: str = "wait",
    actor_id: str = "",
    status: str = STATUS_QUEUED,
    start_tick: int = 0,
    end_tick: int = 0,
    duration_ticks: int = DEFAULT_DURATION_TICKS,
    target: Optional[Dict] = None,
    parameters: Optional[Dict] = None,
    resolution_config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Create a canonical Long Action structure."""
    if action_id is None:
        action_id = "act_" + str(uuid.uuid4())[:8]

    return {
        "action_id": action_id,
        "action_type": action_type,
        "actor_id": actor_id,
        "status": status,
        "start_tick": start_tick,
        "end_tick": end_tick,
        "duration_ticks": duration_ticks,
        "target": target,
        "parameters": parameters or {},
        "resolution_config": resolution_config or {},
    }


def validate_long_action(action: Dict[str, Any]) -> List[str]:
    """Validate a long action structure. Returns list of errors (empty = valid)."""
    errors = []
    required = ["action_id", "action_type", "actor_id", "status", "start_tick", "end_tick", "duration_ticks"]
    for field in required:
        if field not in action:
            errors.append(f"Missing required field: {field}")
    if action.get("status") not in VALID_STATUSES:
        errors.append(f"Invalid status: {action.get('status')}")
    return errors


# ============ ACTION QUEUE ============


class ActionQueue:
    """Runtime action storage for long actions.

    Manages the lifecycle of long actions for all actors.
    One active long action per actor (default).
    """

    def __init__(self):
        self._actions: Dict[str, Dict[str, Any]] = {}
        self._actor_actions: Dict[str, str] = {}
        self._events: List[Dict[str, Any]] = []

    def queue_action(
        self,
        actor_id: str,
        action_type: str,
        duration_ticks: int = DEFAULT_DURATION_TICKS,
        current_tick: int = 0,
        target: Optional[Dict] = None,
        parameters: Optional[Dict] = None,
        resolution_config: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """Queue a new long action for an actor.

        Returns None if actor already has an active action.
        """
        if actor_id in self._actor_actions:
            existing_id = self._actor_actions[actor_id]
            existing = self._actions.get(existing_id)
            if existing and existing["status"] in (STATUS_QUEUED, STATUS_ACTIVE):
                return None

        action = create_long_action(
            action_type=action_type,
            actor_id=actor_id,
            status=STATUS_QUEUED,
            start_tick=current_tick,
            end_tick=current_tick + duration_ticks,
            duration_ticks=duration_ticks,
            target=target,
            parameters=parameters,
            resolution_config=resolution_config,
        )

        self._actions[action["action_id"]] = action
        self._actor_actions[actor_id] = action["action_id"]
        self._generate_event(EVENT_ACTION_STARTED, action, current_tick)

        return action

    def cancel_action(self, action_id: str, current_tick: int = 0) -> bool:
        """Cancel an action. Returns True if cancelled."""
        action = self._actions.get(action_id)
        if not action:
            return False
        if action["status"] in (STATUS_COMPLETED, STATUS_CANCELLED, STATUS_FAILED):
            return False

        action["status"] = STATUS_CANCELLED
        actor_id = action["actor_id"]
        if actor_id in self._actor_actions and self._actor_actions[actor_id] == action_id:
            del self._actor_actions[actor_id]
        self._generate_event(EVENT_ACTION_CANCELLED, action, current_tick)
        return True

    def get_actor_action(self, actor_id: str) -> Optional[Dict[str, Any]]:
        """Get the current action for an actor.
        
        Only returns actions that are still queued or active.
        Completed/cancelled/failed actions are not returned (they're done).
        """
        action_id = self._actor_actions.get(actor_id)
        if action_id:
            action = self._actions.get(action_id)
            if action and action["status"] in (STATUS_QUEUED, STATUS_ACTIVE):
                print(f"[ACTION DEBUG] get_actor_action({actor_id}): found active action {action_id}, status={action['status']}, end_tick={action['end_tick']}")
                return action
            # Action exists but is completed/cancelled/failed - actor is free
            if action:
                print(f"[ACTION DEBUG] get_actor_action({actor_id}): action {action_id} is {action['status']} (actor is free)")
        print(f"[ACTION DEBUG] get_actor_action({actor_id}): no active action found")
        return None

    def get_active_actions(self) -> List[Dict[str, Any]]:
        """Get all queued or active actions."""
        return [
            a for a in self._actions.values()
            if a["status"] in (STATUS_QUEUED, STATUS_ACTIVE)
        ]

    def get_all_actions(self) -> List[Dict[str, Any]]:
        """Get all actions."""
        return list(self._actions.values())

    def complete_action(self, action_id: str, current_tick: int = 0) -> Optional[Dict[str, Any]]:
        """Complete an action. Returns the completed action or None."""
        action = self._actions.get(action_id)
        if not action:
            return None
        if action["status"] not in (STATUS_QUEUED, STATUS_ACTIVE):
            return None

        action["status"] = STATUS_COMPLETED
        actor_id = action["actor_id"]
        if actor_id in self._actor_actions and self._actor_actions[actor_id] == action_id:
            del self._actor_actions[actor_id]
        self._generate_event(EVENT_ACTION_COMPLETED, action, current_tick)
        return action

    def fail_action(self, action_id: str, current_tick: int = 0) -> Optional[Dict[str, Any]]:
        """Fail an action. Returns the failed action or None."""
        action = self._actions.get(action_id)
        if not action:
            return None
        if action["status"] not in (STATUS_QUEUED, STATUS_ACTIVE):
            return None

        action["status"] = STATUS_FAILED
        actor_id = action["actor_id"]
        if actor_id in self._actor_actions and self._actor_actions[actor_id] == action_id:
            del self._actor_actions[actor_id]
        self._generate_event(EVENT_ACTION_FAILED, action, current_tick)
        return action

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all generated events."""
        return list(self._events)

    def clear_events(self):
        """Clear all events."""
        self._events.clear()

    def _generate_event(self, event_type: str, action: Dict[str, Any], tick: int):
        """Generate an event for an action lifecycle change."""
        event = {
            "event_type": event_type,
            "action_id": action["action_id"],
            "action_type": action["action_type"],
            "actor_id": action["actor_id"],
            "status": action["status"],
            "tick": tick,
            "timestamp": time.time(),
            "data": {
                "duration_ticks": action["duration_ticks"],
                "start_tick": action["start_tick"],
                "end_tick": action["end_tick"],
            },
        }
        self._events.append(event)


# ============ TICK INTEGRATION ============


def process_tick(queue: ActionQueue, current_tick: int, resolve_callback: Optional[Callable] = None):
    """Process a world tick for all long actions.

    When tick advances:
    - queued -> active (and immediately complete if end_tick reached)
    - active actions progress and complete when end_tick is reached
    
    Returns list of results from resolve_callback (if provided).
    """
    results = []
    for action in queue.get_all_actions():
        if action["status"] == STATUS_QUEUED:
            action["status"] = STATUS_ACTIVE
            # Check if 1-tick action can complete immediately
            if current_tick >= action["end_tick"]:
                completed = queue.complete_action(action["action_id"], current_tick)
                if completed and resolve_callback:
                    result = resolve_callback(completed, current_tick)
                    if result is not None:
                        results.append(result)
                continue  # Skip second check below

        elif action["status"] == STATUS_ACTIVE:
            if current_tick >= action["end_tick"]:
                completed = queue.complete_action(action["action_id"], current_tick)
                if completed and resolve_callback:
                    result = resolve_callback(completed, current_tick)
                    if result is not None:
                        results.append(result)
    
    return results


# ============ RESOLUTION INTEGRATION ============


def resolve_long_action(
    action: Dict[str, Any],
    current_tick: int,
    actor: Optional[Dict] = None,
    target: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Resolve a completed long action using the Action Resolution Engine."""
    from engine.action_resolution import resolve_action, ACTION_TYPE_WORLD, ACTION_TYPE_OPPOSED

    resolution_config = action.get("resolution_config", {})
    action_type = resolution_config.get("action_type", ACTION_TYPE_WORLD)
    attribute_name = resolution_config.get("attribute_name", "observation")
    difficulty = resolution_config.get("difficulty", 60)
    technique_name = resolution_config.get("technique_name")
    target_attribute_name = resolution_config.get("target_attribute_name")
    modifiers = resolution_config.get("modifiers")

    if action_type == ACTION_TYPE_OPPOSED and target and target_attribute_name:
        return resolve_action(
            action_type=ACTION_TYPE_OPPOSED,
            actor=actor or {"attributes": {}, "techniques": {}},
            attribute_name=attribute_name,
            target=target,
            target_attribute_name=target_attribute_name,
            technique_name=technique_name,
            modifiers=modifiers,
        )
    else:
        return resolve_action(
            action_type=ACTION_TYPE_WORLD,
            actor=actor or {"attributes": {}, "techniques": {}},
            attribute_name=attribute_name,
            difficulty=difficulty,
            technique_name=technique_name,
            modifiers=modifiers,
        )


# ============ FRAMEWORK TEST ACTIONS ============


def create_wait_action(
    actor_id: str,
    duration_ticks: int = 1,
    current_tick: int = 0,
) -> Dict[str, Any]:
    """Create a wait action (framework validation only)."""
    return create_long_action(
        action_type="wait",
        actor_id=actor_id,
        duration_ticks=duration_ticks,
        start_tick=current_tick,
        end_tick=current_tick + duration_ticks,
        parameters={"description": "Waiting"},
        resolution_config={
            "action_type": "world",
            "attribute_name": "observation",
            "difficulty": 20,
        },
    )


def create_observe_action(
    actor_id: str,
    duration_ticks: int = 2,
    current_tick: int = 0,
    target: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Create an observe action (framework validation only)."""
    return create_long_action(
        action_type="observe",
        actor_id=actor_id,
        duration_ticks=duration_ticks,
        start_tick=current_tick,
        end_tick=current_tick + duration_ticks,
        target=target,
        parameters={"description": "Observing surroundings"},
        resolution_config={
            "action_type": "world",
            "attribute_name": "observation",
            "difficulty": 40,
        },
    )


def create_rest_action(
    actor_id: str,
    duration_ticks: int = 3,
    current_tick: int = 0,
) -> Dict[str, Any]:
    """Create a rest action (framework validation only)."""
    return create_long_action(
        action_type="rest",
        actor_id=actor_id,
        duration_ticks=duration_ticks,
        start_tick=current_tick,
        end_tick=current_tick + duration_ticks,
        parameters={"description": "Resting to recover"},
        resolution_config={
            "action_type": "world",
            "attribute_name": "constitution",
            "difficulty": 20,
        },
    )


# ============ DEMO ============


def run_demo():
    """Demonstrate the long action framework."""
    print("=" * 60)
    print("LONG ACTION FRAMEWORK - DEMO")
    print("=" * 60)

    queue = ActionQueue()

    # Player queues a wait action
    print("\n--- Tick 0: Player queues wait action ---")
    action = queue.queue_action(
        actor_id="player",
        action_type="wait",
        duration_ticks=2,
        current_tick=0,
    )
    print(f"Action: {action['action_id']}")
    print(f"Status: {action['status']}")
    print(f"End tick: {action['end_tick']}")

    # Player tries to queue another action (should fail)
    print("\n--- Player tries to queue another action ---")
    result = queue.queue_action(
        actor_id="player",
        action_type="observe",
        duration_ticks=1,
        current_tick=0,
    )
    print(f"Result: {result} (None = blocked)")

    # Process tick 1
    print("\n--- Tick 1 ---")
    process_tick(queue, 1)
    player_action = queue.get_actor_action("player")
    print(f"Player action status: {player_action['status']}")

    # Process tick 2 (action completes)
    print("\n--- Tick 2 ---")
    process_tick(queue, 2)
    player_action = queue.get_actor_action("player")
    print(f"Player action: {player_action} (None = completed)")

    # Check events
    print("\n--- Events ---")
    events = queue.get_events()
    for event in events:
        print(f"  {event['event_type']}: {event['action_type']} ({event['status']})")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()