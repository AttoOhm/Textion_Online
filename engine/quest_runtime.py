"""
Quest Runtime State Management

Tracks quest progress, completion conditions, and rewards.
Single source of truth for player quest state.
"""

import json


class QuestRuntimeState:
    """Manages quest runtime state for a player."""
    
    def __init__(self, player_id):
        self.player_id = player_id
        self.active_quests = {}  # quest_id -> quest state
        self.completed_quests = {}  # quest_id -> completion data
        self.failed_quests = {}  # quest_id -> failure data
        self.rewards_claimed = {}  # quest_id -> rewards claimed
    
    def accept_quest(self, quest_id, quest_data):
        """
        Accept a quest and initialize its runtime state.
        
        Args:
            quest_id: Quest ID to accept
            quest_data: Quest definition data
        """
        if quest_id in self.active_quests:
            return False  # Already active
        
        self.active_quests[quest_id] = {
            "quest_id": quest_id,
            "status": "active",
            "completed_conditions": [],
            "reward_claimed": False,
            "accepted_at": "now",
            "quest_data": quest_data
        }
        return True
    
    def update_condition_progress(self, quest_id, condition_index, met=True):
        """
        Update progress on a specific condition.
        
        Args:
            quest_id: Quest ID
            condition_index: Index of the condition
            met: Whether the condition is now met
        """
        if quest_id not in self.active_quests:
            return False
        
        quest_state = self.active_quests[quest_id]
        completed = quest_state["completed_conditions"]
        
        if condition_index not in completed:
            completed.append(condition_index)
        
        return True
    
    def complete_quest(self, quest_id, rewards=None):
        """
        Mark a quest as completed and grant rewards.
        
        Args:
            quest_id: Quest ID to complete
            rewards: Rewards to grant
        """
        if quest_id not in self.active_quests:
            return False
        
        quest_state = self.active_quests.pop(quest_id)
        quest_state["status"] = "completed"
        quest_state["completed_at"] = "now"
        
        self.completed_quests[quest_id] = quest_state
        
        if rewards:
            self.rewards_claimed[quest_id] = rewards
        
        return True
    
    def fail_quest(self, quest_id, reason=""):
        """
        Mark a quest as failed.
        
        Args:
            quest_id: Quest ID to fail
            reason: Reason for failure
        """
        if quest_id not in self.active_quests:
            return False
        
        quest_state = self.active_quests.pop(quest_id)
        quest_state["status"] = "failed"
        quest_state["failed_at"] = "now"
        quest_state["failure_reason"] = reason
        
        self.failed_quests[quest_id] = quest_state
        
        return True
    
    def is_quest_active(self, quest_id):
        """Check if a quest is currently active"""
        return quest_id in self.active_quests
    
    def is_quest_completed(self, quest_id):
        """Check if a quest has been completed"""
        return quest_id in self.completed_quests
    
    def is_quest_failed(self, quest_id):
        """Check if a quest has been failed"""
        return quest_id in self.failed_quests
    
    def get_active_quests(self):
        """Get all active quests"""
        return self.active_quests
    
    def get_completed_quests(self):
        """Get all completed quests"""
        return self.completed_quests
    
    def get_failed_quests(self):
        """Get all failed quests"""
        return self.failed_quests
    
    def get_quest_state(self, quest_id):
        """Get the state of a specific quest"""
        if quest_id in self.active_quests:
            return self.active_quests[quest_id]
        elif quest_id in self.completed_quests:
            return self.completed_quests[quest_id]
        elif quest_id in self.failed_quests:
            return self.failed_quests[quest_id]
        return None
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            "player_id": self.player_id,
            "active_quests": self.active_quests,
            "completed_quests": self.completed_quests,
            "failed_quests": self.failed_quests,
            "rewards_claimed": self.rewards_claimed
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        state = cls(data.get("player_id", "default_player"))
        state.active_quests = data.get("active_quests", {})
        state.completed_quests = data.get("completed_quests", {})
        state.failed_quests = data.get("failed_quests", {})
        state.rewards_claimed = data.get("rewards_claimed", {})
        return state


# Global quest runtime states
_quest_runtime_states = {}


def get_quest_runtime_state(player_id):
    """Get or create quest runtime state for a player"""
    if player_id not in _quest_runtime_states:
        _quest_runtime_states[player_id] = QuestRuntimeState(player_id)
    return _quest_runtime_states[player_id]


def accept_quest(player_id, quest_id, quest_data):
    """Accept a quest for a player"""
    state = get_quest_runtime_state(player_id)
    return state.accept_quest(quest_id, quest_data)


def complete_quest(player_id, quest_id, rewards=None):
    """Complete a quest for a player"""
    state = get_quest_runtime_state(player_id)
    return state.complete_quest(quest_id, rewards)


def fail_quest(player_id, quest_id, reason=""):
    """Fail a quest for a player"""
    state = get_quest_runtime_state(player_id)
    return state.fail_quest(quest_id, reason)


def is_quest_active(player_id, quest_id):
    """Check if a quest is active for a player"""
    state = get_quest_runtime_state(player_id)
    return state.is_quest_active(quest_id)


def is_quest_completed(player_id, quest_id):
    """Check if a quest is completed for a player"""
    state = get_quest_runtime_state(player_id)
    return state.is_quest_completed(quest_id)