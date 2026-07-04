"""
Quest Completion Condition Evaluator

Evaluates completion_conditions from quest definitions.
Single source of truth for quest completion logic.
"""

import os
import json


class QuestEvaluator:
    """Evaluates quest completion conditions against world state."""
    
    def __init__(self):
        self.quest_definitions = {}
        self._load_quest_definitions()
    
    def _load_quest_definitions(self):
        """Load all quest definitions from data/quests/*.json (including subdirectories)"""
        quests_dir = os.path.join('data', 'quests')
        if os.path.exists(quests_dir):
            for root, dirs, files in os.walk(quests_dir):
                for filename in files:
                    if filename.endswith('.json'):
                        filepath = os.path.join(root, filename)
                        with open(filepath, 'r') as f:
                            try:
                                data = json.load(f)
                                quest_id = data.get('id', filename.replace('.json', '').lower())
                                self.quest_definitions[quest_id] = data
                            except Exception as e:
                                print(f"Failed to load quest {filename}: {e}")
    
    def get_quest_definition(self, quest_id):
        """Get quest definition by ID"""
        return self.quest_definitions.get(quest_id)
    
    def evaluate_completion_conditions(self, quest_id, world_state, player_state):
        """
        Evaluate all completion conditions for a quest.
        
        Args:
            quest_id: Quest ID to evaluate
            world_state: Current world state (NPCs, locations, events)
            player_state: Player's current state (inventory, quests, etc.)
        
        Returns:
            dict: { "completed": bool, "conditions_met": list, "conditions_pending": list }
        """
        quest_def = self.get_quest_definition(quest_id)
        if not quest_def:
            return {"completed": False, "conditions_met": [], "conditions_pending": [], "error": "Quest not found"}
        
        completion_conditions = quest_def.get('completion_conditions', [])
        if not completion_conditions:
            return {"completed": False, "conditions_met": [], "conditions_pending": [], "error": "No completion conditions defined"}
        
        conditions_met = []
        conditions_pending = []
        
        for i, condition in enumerate(completion_conditions):
            condition_type = condition.get('type', '')
            
            if condition_type == 'talk':
                result = self._evaluate_talk_condition(condition, world_state, player_state)
            elif condition_type == 'kill':
                result = self._evaluate_kill_condition(condition, world_state, player_state)
            elif condition_type == 'collect':
                result = self._evaluate_collect_condition(condition, world_state, player_state)
            elif condition_type == 'explore':
                result = self._evaluate_explore_condition(condition, world_state, player_state)
            elif condition_type == 'investigate':
                result = self._evaluate_investigate_condition(condition, world_state, player_state)
            elif condition_type == 'deliver':
                result = self._evaluate_deliver_condition(condition, world_state, player_state)
            elif condition_type == 'location_discovered':
                result = self._evaluate_location_discovered_condition(condition, world_state, player_state)
            elif condition_type == 'be_at_location':
                result = self._evaluate_be_at_location_condition(condition, world_state, player_state)
            elif condition_type == 'stat':
                result = self._evaluate_stat_condition(condition, world_state, player_state)
            elif condition_type == 'action_count':
                result = self._evaluate_action_count_condition(condition, world_state, player_state)
            elif condition_type == 'kill_unique':
                result = self._evaluate_kill_unique_condition(condition, world_state, player_state)
            else:
                result = {"met": False, "reason": f"Unknown condition type: {condition_type}"}
            
            condition_entry = {
                "index": i,
                "type": condition_type,
                "target": condition.get('target', ''),
                "topic": condition.get('topic', ''),
                "count": condition.get('count', 1),
                "met": result.get('met', False),
                "reason": result.get('reason', ''),
                "current": result.get('current', 0)
            }
            
            if result.get('met', False):
                conditions_met.append(condition_entry)
            else:
                conditions_pending.append(condition_entry)
        
        all_met = len(conditions_pending) == 0
        
        return {
            "completed": all_met,
            "conditions_met": conditions_met,
            "conditions_pending": conditions_pending
        }
    
    def _evaluate_talk_condition(self, condition, world_state, player_state):
        """
        Evaluate a talk completion condition.
        
        Condition: { "type": "talk", "target": "aldric", "topic": "wolves" }
        
        World Event: Player talked to target NPC about topic
        """
        target_npc = condition.get('target', '').lower()
        topic = condition.get('topic', '').lower()
        
        # Check conversation history for this talk event
        conversation_histories = world_state.get('conversation_histories', {})
        player_id = player_state.get('id', 'default_player')
        
        # Check if player has talked to target NPC about topic
        npc_conversations = conversation_histories.get(player_id, {})
        target_conversations = npc_conversations.get(target_npc, {})
        history = target_conversations.get('history', [])
        
        for entry in history:
            if entry.get('speaker') == 'player':
                text = entry.get('text', '').lower()
                # Check if the conversation topic was mentioned
                if topic in text:
                    return {"met": True, "reason": f"Player talked to {target_npc} about {topic}"}
        
        # Also check if the conversation topic was discussed (broader match)
        for entry in history:
            if entry.get('speaker') == 'player':
                text = entry.get('text', '').lower()
                # Check for topic keywords
                topic_words = topic.split('_')
                if any(word in text for word in topic_words):
                    return {"met": True, "reason": f"Player discussed {topic} with {target_npc}"}
        
        return {"met": False, "reason": f"Player has not talked to {target_npc} about {topic}"}
    
    def _evaluate_kill_condition(self, condition, world_state, player_state):
        """
        Evaluate a kill completion condition.
        
        Condition: { "type": "kill", "target": "wolf", "count": 5 }
        
        World Event: Player killed target creatures
        """
        target = condition.get('target', '').lower()
        required_count = condition.get('count', 1)
        
        # Check combat events for kills
        combat_events = world_state.get('combat_events', {})
        player_id = player_state.get('id', 'default_player')
        player_kills = combat_events.get(player_id, {})
        
        current_count = player_kills.get(target, 0)
        
        if current_count >= required_count:
            return {"met": True, "reason": f"Player killed {current_count} {target}(s)", "current": current_count}
        else:
            return {"met": False, "reason": f"Player killed {current_count}/{required_count} {target}(s)", "current": current_count}
    
    def _evaluate_collect_condition(self, condition, world_state, player_state):
        """
        Evaluate a collect completion condition.
        
        Condition: { "type": "collect", "target": "moonflower", "count": 3 }
        
        World Event: Player collected target items
        """
        target = condition.get('target', '').lower()
        required_count = condition.get('count', 1)
        
        # Check inventory for items
        inventory = player_state.get('inventory', [])
        current_count = sum(1 for item in inventory if item.get('id', '').lower() == target or item.get('name', '').lower() == target)
        
        if current_count >= required_count:
            return {"met": True, "reason": f"Player has {current_count} {target}(s)", "current": current_count}
        else:
            return {"met": False, "reason": f"Player has {current_count}/{required_count} {target}(s)", "current": current_count}
    
    def _evaluate_explore_condition(self, condition, world_state, player_state):
        """
        Evaluate an explore completion condition.
        
        Condition: { "type": "explore", "target": "village_walls" }
        
        World Event: Player visited target location
        """
        target_location = condition.get('target', '').lower()
        
        # Check visited locations
        visited_locations = world_state.get('visited_locations', {})
        player_id = player_state.get('id', 'default_player')
        player_visited = visited_locations.get(player_id, [])
        
        if target_location in player_visited:
            return {"met": True, "reason": f"Player visited {target_location}"}
        else:
            return {"met": False, "reason": f"Player has not visited {target_location}"}
    
    def _evaluate_investigate_condition(self, condition, world_state, player_state):
        """
        Evaluate an investigate completion condition.
        
        Condition: { "type": "investigate", "target": "noise_source" }
        
        World Event: Player investigated target
        """
        target = condition.get('target', '').lower()
        
        # Check investigation events
        investigation_events = world_state.get('investigation_events', {})
        player_id = player_state.get('id', 'default_player')
        player_investigations = investigation_events.get(player_id, [])
        
        if target in player_investigations:
            return {"met": True, "reason": f"Player investigated {target}"}
        else:
            return {"met": False, "reason": f"Player has not investigated {target}"}
    
    def _evaluate_deliver_condition(self, condition, world_state, player_state):
        """
        Evaluate a deliver completion condition.
        
        Condition: { "type": "deliver", "target": "elias", "item": "spice_crate" }
        
        World Event: Player delivered item to target NPC
        """
        target_npc = condition.get('target', '').lower()
        target_item = condition.get('item', '').lower()
        
        # Check delivery events
        delivery_events = world_state.get('delivery_events', {})
        player_id = player_state.get('id', 'default_player')
        player_deliveries = delivery_events.get(player_id, [])
        
        for delivery in player_deliveries:
            if delivery.get('npc', '').lower() == target_npc and delivery.get('item', '').lower() == target_item:
                return {"met": True, "reason": f"Player delivered {target_item} to {target_npc}"}
        
        return {"met": False, "reason": f"Player has not delivered {target_item} to {target_npc}"}
    
    def _evaluate_location_discovered_condition(self, condition, world_state, player_state):
        """
        Evaluate a location_discovered completion condition.
        
        Condition: { "type": "location_discovered", "target": "village_walls" }
        
        World State: Player has discovered the target location.
        Uses player_state.discovery.known_locations (stable location IDs).
        """
        target_location = condition.get('target', '').lower()
        
        # Check player's known_locations from discovery system
        discovery = player_state.get('discovery', {})
        known_locations = discovery.get('known_locations', [])
        
        if target_location in known_locations:
            return {"met": True, "reason": f"Player discovered {target_location}"}
        else:
            return {"met": False, "reason": f"Player has not discovered {target_location}"}
    
    def _evaluate_be_at_location_condition(self, condition, world_state, player_state):
        """
        Evaluate a be_at_location completion condition.

        Condition: { "type": "be_at_location", "target": "village_walls", "time_of_day": "night" }

        World State: Player is at the target location.
        Optional: time_of_day filter (morning, afternoon, evening, night).
        Uses player_state.position {map_id, node_id}.
        """
        target_location = condition.get('target', '').lower()
        required_time = condition.get('time_of_day', '').lower()

        # Check player's current position
        position = player_state.get('position', {})
        current_map = position.get('map_id', '')
        current_node = position.get('node_id', '')

        # Check if player is at the target location (matches either map_id or node_id)
        at_location = (current_map == target_location or current_node == target_location)

        if not at_location:
            return {"met": False, "reason": f"Player is not at {target_location} (currently at {current_map}/{current_node})"}

        # Check time of day if specified
        if required_time:
            current_time_of_day = world_state.get('time_of_day', '')
            if current_time_of_day != required_time:
                return {"met": False, "reason": f"Player is at {target_location} but it is {current_time_of_day}, not {required_time}"}

        return {"met": True, "reason": f"Player is at {target_location}"}

    def _evaluate_stat_condition(self, condition, world_state, player_state):
        """
        Evaluate a stat completion condition.

        Condition: { "type": "stat", "target": "total_sword_damage", "count": 1000 }

        World State: Player has accumulated enough of a specific stat.
        Uses player_state.stats dictionary.
        """
        target_stat = condition.get('target', '').lower()
        required_count = condition.get('count', 1)

        # Check player stats
        stats = player_state.get('stats', {})
        current_count = stats.get(target_stat, 0)

        if current_count >= required_count:
            return {"met": True, "reason": f"Player has {current_count} {target_stat}", "current": current_count}
        else:
            return {"met": False, "reason": f"Player has {current_count}/{required_count} {target_stat}", "current": current_count}

    def _evaluate_action_count_condition(self, condition, world_state, player_state):
        """
        Evaluate an action_count completion condition.

        Condition: { "type": "action_count", "target": "attack_old_oak", "count": 100 }

        World State: Player has performed a specific action a number of times.
        Uses player_state.action_counts dictionary.
        """
        target_action = condition.get('target', '').lower()
        required_count = condition.get('count', 1)

        # Check action counts
        action_counts = player_state.get('action_counts', {})
        current_count = action_counts.get(target_action, 0)

        if current_count >= required_count:
            return {"met": True, "reason": f"Player performed {current_count} {target_action} actions", "current": current_count}
        else:
            return {"met": False, "reason": f"Player performed {current_count}/{required_count} {target_action} actions", "current": current_count}

    def _evaluate_kill_unique_condition(self, condition, world_state, player_state):
        """
        Evaluate a kill_unique completion condition.

        Condition: { "type": "kill_unique", "target": "creature_types", "count": 20 }

        World State: Player has killed unique creature types.
        Uses player_state.unique_kills set/list.
        """
        required_count = condition.get('count', 1)

        # Check unique kills
        unique_kills = player_state.get('unique_kills', [])
        current_count = len(unique_kills) if isinstance(unique_kills, list) else 0

        if current_count >= required_count:
            return {"met": True, "reason": f"Player defeated {current_count} unique creature types", "current": current_count}
        else:
            return {"met": False, "reason": f"Player defeated {current_count}/{required_count} unique creature types", "current": current_count}


# Global evaluator instance
quest_evaluator = QuestEvaluator()


def evaluate_quest_completion(quest_id, world_state, player_state):
    """
    Convenience function to evaluate quest completion.
    
    Args:
        quest_id: Quest ID to evaluate
        world_state: Current world state
        player_state: Player's current state
    
    Returns:
        dict: Completion evaluation result
    """
    return quest_evaluator.evaluate_completion_conditions(quest_id, world_state, player_state)


def get_quest_definition(quest_id):
    """Get quest definition by ID"""
    return quest_evaluator.get_quest_definition(quest_id)