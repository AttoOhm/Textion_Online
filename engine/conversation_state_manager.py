"""
Conversation State Manager (Layer 2)

Manages 3-tier conversation state system:
- Tier 1: Mode (general, quest, information, shop, trade, repair, crafting)
- Tier 2: Substate (awaiting_topic_selection, awaiting_item_selection, etc.)
- Tier 3: Context (active quest, current topic, selected item, etc.)

This module is responsible for:
- State transitions
- State validation
- Timeout handling
- Context management
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import time


class Mode(Enum):
    """Tier 1: Conversation mode"""
    GENERAL = "general"
    QUEST = "quest"
    INFORMATION = "information"
    SHOP = "shop"
    TRADE = "trade"
    REPAIR = "repair"
    CRAFTING = "crafting"


class Substate(Enum):
    """Tier 2: Conversation substate"""
    NONE = None
    AWAITING_TOPIC_SELECTION = "awaiting_topic_selection"
    AWAITING_ITEM_SELECTION = "awaiting_item_selection"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    AWAITING_QUANTITY = "awaiting_quantity"
    AWAITING_PAYMENT = "awaiting_payment"


class ConversationState:
    """Manages 3-tier conversation state for a single conversation."""
    
    def __init__(self, npc_id: str, player_id: str):
        """Initialize conversation state."""
        self.npc_id = npc_id
        self.player_id = player_id
        
        # Tier 1: Mode
        self.mode = Mode.GENERAL
        
        # Tier 2: Substate
        self.substate = Substate.NONE
        
        # Tier 3: Context
        self.context = {
            'active_quest': None,
            'current_topic': None,
            'selected_item': None,
            'available_topics': [],
            'available_items': [],
            'unlocked_knowledge': [],
            'negotiation': {},
            'pending_action': None,
            'state_timestamp': time.time()
        }
        
        # History
        self.history = []
        self.childish_warnings = 0
    
    def set_state(self, mode: Mode, substate: Substate = Substate.NONE, 
                  context_updates: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Set conversation state.
        
        Args:
            mode: New mode
            substate: New substate
            context_updates: Context data to update
        
        Returns:
            Memory updates dict for Layer 1 to apply
        """
        self.mode = mode
        self.substate = substate
        self.context['state_timestamp'] = time.time()
        
        if context_updates:
            self.context.update(context_updates)
        
        # Build memory updates
        memory_updates = {
            'state': self._build_state_string(),
            'state_timestamp': self.context['state_timestamp']
        }
        
        if context_updates:
            memory_updates['context_updates'] = context_updates
        
        return memory_updates
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state information."""
        return {
            'mode': self.mode.value,
            'substate': self.substate.value if self.substate else None,
            'context': self.context.copy(),
            'history': self.history,
            'childish_warnings': self.childish_warnings
        }
    
    def get_mode(self) -> Mode:
        """Get current mode."""
        return self.mode
    
    def get_substate(self) -> Substate:
        """Get current substate."""
        return self.substate
    
    def get_context(self) -> Dict[str, Any]:
        """Get current context."""
        return self.context.copy()
    
    def check_timeout(self, timeout_seconds: float = 300.0) -> bool:
        """
        Check if state has timed out.
        
        Args:
            timeout_seconds: Timeout duration (default 5 minutes)
        
        Returns:
            True if timed out, False otherwise
        """
        elapsed = time.time() - self.context['state_timestamp']
        return elapsed > timeout_seconds
    
    def reset_to_general(self) -> Dict[str, Any]:
        """
        Reset state to general mode.
        
        Returns:
            Memory updates dict
        """
        return self.set_state(Mode.GENERAL, Substate.NONE, {
            'active_quest': None,
            'current_topic': None,
            'selected_item': None,
            'available_topics': [],
            'available_items': [],
            'negotiation': {},
            'pending_action': None
        })
    
    def _build_state_string(self) -> str:
        """Build state string for backward compatibility."""
        if self.substate == Substate.NONE:
            return self.mode.value
        return f"{self.mode.value}:{self.substate.value}"
    
    def parse_state_string(self, state_string: str):
        """
        Parse state string (for backward compatibility).
        
        Args:
            state_string: State string like "general" or "shop:awaiting_item_selection"
        """
        parts = state_string.split(':')
        
        # Parse mode
        mode_str = parts[0]
        try:
            self.mode = Mode(mode_str)
        except ValueError:
            self.mode = Mode.GENERAL
        
        # Parse substate
        if len(parts) > 1:
            substate_str = parts[1]
            try:
                self.substate = Substate(substate_str)
            except ValueError:
                self.substate = Substate.NONE
        else:
            self.substate = Substate.NONE


class ConversationStateManager:
    """Manages conversation states for all active conversations."""
    
    def __init__(self):
        """Initialize state manager."""
        self.states: Dict[str, ConversationState] = {}
        self.timeout_seconds = 300.0  # 5 minutes
    
    def get_or_create_state(self, player_id: str, npc_id: str) -> ConversationState:
        """
        Get or create conversation state.
        
        Args:
            player_id: Player ID
            npc_id: NPC ID
        
        Returns:
            ConversationState instance
        """
        key = f"{player_id}:{npc_id}"
        
        if key not in self.states:
            self.states[key] = ConversationState(npc_id, player_id)
        
        return self.states[key]
    
    def get_state(self, player_id: str, npc_id: str) -> Optional[ConversationState]:
        """
        Get conversation state if exists.
        
        Args:
            player_id: Player ID
            npc_id: NPC ID
        
        Returns:
            ConversationState or None
        """
        key = f"{player_id}:{npc_id}"
        return self.states.get(key)
    
    def remove_state(self, player_id: str, npc_id: str):
        """
        Remove conversation state.
        
        Args:
            player_id: Player ID
            npc_id: NPC ID
        """
        key = f"{player_id}:{npc_id}"
        if key in self.states:
            del self.states[key]
    
    def check_timeouts(self) -> List[Dict[str, Any]]:
        """
        Check all states for timeouts.
        
        Returns:
            List of timeout events (player_id, npc_id)
        """
        timeouts = []
        
        for key, state in self.states.items():
            if state.check_timeout(self.timeout_seconds):
                player_id, npc_id = key.split(':')
                timeouts.append({
                    'player_id': player_id,
                    'npc_id': npc_id,
                    'state': state.get_state()
                })
        
        return timeouts
    
    def handle_timeout(self, player_id: str, npc_id: str) -> Dict[str, Any]:
        """
        Handle state timeout by resetting to general.
        
        Args:
            player_id: Player ID
            npc_id: NPC ID
        
        Returns:
            Memory updates dict
        """
        state = self.get_state(player_id, npc_id)
        if state:
            return state.reset_to_general()
        return {}


# Global state manager instance
state_manager = ConversationStateManager()


def get_or_create_state(player_id: str, npc_id: str) -> ConversationState:
    """Convenience function to get or create state."""
    return state_manager.get_or_create_state(player_id, npc_id)


def get_state(player_id: str, npc_id: str) -> Optional[ConversationState]:
    """Convenience function to get state."""
    return state_manager.get_state(player_id, npc_id)


def remove_state(player_id: str, npc_id: str):
    """Convenience function to remove state."""
    state_manager.remove_state(player_id, npc_id)


def check_timeouts() -> List[Dict[str, Any]]:
    """Convenience function to check timeouts."""
    return state_manager.check_timeouts()


def handle_timeout(player_id: str, npc_id: str) -> Dict[str, Any]:
    """Convenience function to handle timeout."""
    return state_manager.handle_timeout(player_id, npc_id)