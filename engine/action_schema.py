"""
Action Schema — Formal structure for pending player actions.

Actions represent commands submitted by the player that are queued
for execution on the next game tick. The Action schema provides a
canonical format for all player actions, replacing the legacy
string-based pending_commands system.

ACTION FLOW:
  Player input -> Action Schema (validated) -> Pending Queue -> Tick Execution

ACTION FORMAT:
  {
      "action_id": "act_a1b2c3d4",
      "actor_id": "default_player",
      "action_type": "move",
      "target": {"map_id": "village", "node_id": "blacksmith"},
      "submitted_tick": 142,
      "status": "pending"  # pending, executing, completed, failed
  }
"""

import uuid
import threading
from enum import Enum


# Action status lifecycle
class ActionStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


# Valid action types for validation
VALID_ACTION_TYPES = frozenset([
    'move',
    'attack',
    'equip',
    'use',
    'sit',
    'hide',
    'punch',
    'craft',
])

# Global pending action queue
_action_queue = []
_queue_lock = threading.Lock()


def _generate_action_id():
    """Generate a short unique action ID."""
    return 'act_' + str(uuid.uuid4())[:8]


def create_action(actor_id, action_type, target=None, data=None, submitted_tick=0):
    """Create a validated Action object.
    
    Args:
        actor_id: The actor performing the action (e.g., 'default_player').
        action_type: One of VALID_ACTION_TYPES.
        target: Optional target specification. For 'move' actions, this should
                be a dict with 'map_id' and 'node_id' keys.
        data: Optional dict of additional action-specific data.
        submitted_tick: The game tick when the action was submitted.
    
    Returns:
        The created action dict, or raises ValueError if invalid.
    """
    if action_type not in VALID_ACTION_TYPES:
        raise ValueError(f"Invalid action_type: {action_type}. Must be one of {VALID_ACTION_TYPES}")
    
    action = {
        'action_id': _generate_action_id(),
        'actor_id': actor_id,
        'action_type': action_type,
        'target': target or {},
        'data': data or {},
        'submitted_tick': submitted_tick,
        'status': ActionStatus.PENDING.value,
    }
    
    return action


def queue_action(action):
    """Add an action to the pending queue.
    
    Args:
        action: The action dict from create_action().
    
    Returns:
        The action_id of the queued action.
    """
    with _queue_lock:
        _action_queue.append(action)
    return action['action_id']


def get_pending_actions(actor_id=None, action_type=None):
    """Get all pending actions, optionally filtered.
    
    Args:
        actor_id: If provided, only return actions for this actor.
        action_type: If provided, only return actions of this type.
    
    Returns:
        List of pending action dicts.
    """
    with _queue_lock:
        actions = list(_action_queue)
    
    if actor_id:
        actions = [a for a in actions if a.get('actor_id') == actor_id]
    if action_type:
        actions = [a for a in actions if a.get('action_type') == action_type]
    
    return actions


def get_next_action(actor_id):
    """Get the next pending action for an actor (FIFO order).
    
    Args:
        actor_id: The actor to retrieve actions for.
    
    Returns:
        The next action dict, or None if no pending actions.
    """
    with _queue_lock:
        for i, action in enumerate(_action_queue):
            if action.get('actor_id') == actor_id and action.get('status') == ActionStatus.PENDING.value:
                action['status'] = ActionStatus.EXECUTING.value
                return action
    return None


def complete_action(action_id, success=True):
    """Mark an action as completed or failed.
    
    Args:
        action_id: The action_id to update.
        success: True for completed, False for failed.
    """
    new_status = ActionStatus.COMPLETED.value if success else ActionStatus.FAILED.value
    with _queue_lock:
        for action in _action_queue:
            if action['action_id'] == action_id:
                action['status'] = new_status
                break


def clear_completed_actions():
    """Remove completed and failed actions from the queue."""
    with _queue_lock:
        global _action_queue
        _action_queue = [a for a in _action_queue 
                         if a['status'] == ActionStatus.PENDING.value]


def clear_all_actions():
    """Clear all actions from the queue. Useful for testing."""
    with _queue_lock:
        _action_queue.clear()


def get_queue_size():
    """Return the number of pending actions."""
    with _queue_lock:
        return len(_action_queue)