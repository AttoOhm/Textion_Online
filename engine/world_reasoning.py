"""
Layer 2: World Reasoning Engine

Layer 2 analyzes the game world and conversation context to determine:
- What the conversation is about (topic, subtopic)
- What the player and NPC goals are
- What facts should be communicated
- What emotional tone to use
- What type of response is appropriate

Layer 2 does NOT generate dialogue.
Layer 2 does NOT make game state changes (that's the simulation layer).
Layer 2 ONLY reasons about the world state and conversation context.
"""

from typing import Dict, Any, List, Optional
import json
import os


class WorldReasoningEngine:
    """Analyzes world state and conversation to produce reasoning context."""
    
    def __init__(self):
        self.quest_definitions = {}
        self._load_quest_definitions()
    
    def _load_quest_definitions(self):
        """Load all quest definitions from data/quests/*.json"""
        quests_dir = os.path.join('data', 'quests')
        if os.path.exists(quests_dir):
            for filename in os.listdir(quests_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(quests_dir, filename)
                    with open(filepath, 'r') as f:
                        try:
                            data = json.load(f)
                            quest_id = data.get('id', filename.replace('.json', '').lower())
                            self.quest_definitions[quest_id] = data
                        except Exception as e:
                            print(f"Failed to load quest {filename}: {e}")
    
    def reason(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform world reasoning based on Layer 1 intent and game state.
        
        Args:
            input_data: {
                "layer1_result": {"category": "...", "intents": [...], "subject": "..."},
                "player_state": {},
                "actor_state": {},
                "conversation_memory": {},
                "conversation_history": [],  # Full history for context
                "world_state": {}
            }
        
        Returns:
            {
                "conversation_state": {
                    "topic": "...",
                    "subtopic": "...",
                    "current_mode": "...",
                    "player_goal": "...",
                    "npc_goal": "..."
                },
                "world_state": {
                    "active_quest": "...",
                    "quest_stage": "...",
                    "relationship": "...",
                    "known_topics": [...]
                },
                "facts_to_communicate": [...],
                "emotion": "...",
                "recommended_response_type": "...",
                "simulation_packet": {}  # From simulation layer
            }
        """
        layer1_result = input_data.get('layer1_result', {})
        player_state = input_data.get('player_state', {})
        actor_state = input_data.get('actor_state', {})
        conversation_memory = input_data.get('conversation_memory', {})
        conversation_history = input_data.get('conversation_history', [])
        world_state = input_data.get('world_state', {})
        
        # Get category and intent from Layer 1
        category = layer1_result.get('category', 'conversation')
        intents = layer1_result.get('intents', [])
        subject = layer1_result.get('subject')
        primary_intent = intents[0] if intents else 'acknowledgement'
        
        # =========================================================
        # CONVERSATION STATE REASONING
        # =========================================================
        
        # Determine topic based on category and subject
        topic = self._determine_topic(category, subject, conversation_history)
        subtopic = self._determine_subtopic(category, subject, topic)
        current_mode = self._determine_mode(category, primary_intent, conversation_memory)
        
        # Determine goals
        player_goal = self._determine_player_goal(category, primary_intent, subject, conversation_history)
        npc_goal = self._determine_npc_goal(actor_state, category, conversation_memory)
        
        conversation_state = {
            "topic": topic,
            "subtopic": subtopic,
            "current_mode": current_mode,
            "player_goal": player_goal,
            "npc_goal": npc_goal
        }
        
        # =========================================================
        # WORLD STATE REASONING
        # =========================================================
        
        # Check active quests
        active_quest = self._get_active_quest(player_state)
        quest_stage = self._get_quest_stage(player_state, active_quest)
        
        # Determine relationship
        relationship = self._determine_relationship(player_state, actor_state)
        
        # Get known topics (what player has learned from this NPC)
        known_topics = self._get_known_topics(player_state, actor_state)
        
        world_state_reasoned = {
            "active_quest": active_quest,
            "quest_stage": quest_stage,
            "relationship": relationship,
            "known_topics": known_topics
        }
        
        # =========================================================
        # FACTS TO COMMUNICATE
        # =========================================================
        
        facts_to_communicate = self._determine_facts(
            category, primary_intent, subject, actor_state, 
            player_state, conversation_memory
        )
        
        # =========================================================
        # EMOTION AND RESPONSE TYPE
        # =========================================================
        
        emotion = self._determine_emotion(
            category, primary_intent, actor_state, 
            conversation_memory, relationship
        )
        
        response_type = self._determine_response_type(
            category, primary_intent, conversation_memory
        )
        
        # =========================================================
        # RUN SIMULATION (delegate to simulation layer)
        # =========================================================
        
        from engine.conversation_simulator import simulate_conversation
        
        simulation_input = {
            'player_state': player_state,
            'actor_state': actor_state,
            'conversation_memory': conversation_memory,
            'world_state': world_state,
            'layer1_result': layer1_result
        }
        
        simulation_packet = simulate_conversation(simulation_input)
        
        # =========================================================
        # BUILD FINAL OUTPUT
        # =========================================================
        
        return {
            "conversation_state": conversation_state,
            "world_state": world_state_reasoned,
            "facts_to_communicate": facts_to_communicate,
            "emotion": emotion,
            "recommended_response_type": response_type,
            "simulation_packet": simulation_packet
        }
    
    def _determine_topic(self, category: str, subject: Optional[str], 
                        conversation_history: List[Dict]) -> str:
        """Determine the main conversation topic."""
        # Use category as primary topic
        topic_map = {
            'greeting': 'greeting',
            'farewell': 'farewell',
            'information': subject or 'general_information',
            'quest': subject or 'quests',
            'shop': subject or 'shopping',
            'request': subject or 'services',
            'conversation': 'general'
        }
        
        topic = topic_map.get(category, 'general')
        
        # Check conversation history for topic continuity
        if conversation_history and not subject:
            # Look at recent exchanges to infer topic
            recent = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
            for exchange in recent:
                if exchange.get('speaker') == 'npc':
                    # Extract topic from NPC's previous message
                    text = exchange.get('text', '').lower()
                    if 'quest' in text or 'job' in text or 'task' in text:
                        topic = 'quests'
                    elif 'shop' in text or 'buy' in text or 'sell' in text or 'price' in text:
                        topic = 'shopping'
                    elif 'craft' in text or 'forge' in text or 'repair' in text:
                        topic = 'services'
                    break
        
        return topic
    
    def _determine_subtopic(self, category: str, subject: Optional[str], 
                           topic: str) -> str:
        """Determine the subtopic within the main topic."""
        if not subject:
            return "general"
        
        # Specific subtopics based on subject
        if category == 'shop':
            if any(w in subject.lower() for w in ['how much', 'price', 'cost']):
                return "pricing"
            elif any(w in subject.lower() for w in ['buy', 'purchase']):
                return "purchase"
            elif any(w in subject.lower() for w in ['sell']):
                return "selling"
            else:
                return "browsing"
        
        elif category == 'quest':
            if 'accept' in subject.lower() or 'yes' == subject.lower():
                return "acceptance"
            elif 'decline' in subject.lower() or 'no' == subject.lower():
                return "decline"
            else:
                return "inquiry"
        
        elif category == 'request':
            if 'craft' in subject.lower():
                return "crafting"
            elif 'repair' in subject.lower():
                return "repair"
            elif 'train' in subject.lower() or 'teach' in subject.lower():
                return "training"
            else:
                return "service_request"
        
        elif category == 'information':
            return "inquiry"
        
        return "general"
    
    def _determine_mode(self, category: str, intent: str, 
                       conversation_memory: Dict) -> str:
        """Determine the conversation mode."""
        # Check if there's an active conversation state
        current_state = conversation_memory.get('state', 'general')
        
        # Map category to mode
        if category == 'greeting':
            return 'greeting'
        elif category == 'farewell':
            return 'farewell'
        elif category == 'shop':
            return 'shopping'
        elif category == 'quest':
            if intent in ['accept_quest', 'decline_quest']:
                return 'quest_decision'
            else:
                return 'quest_inquiry'
        elif category == 'request':
            return 'service_request'
        elif category == 'information':
            return 'information_sharing'
        else:
            return 'general'
    
    def _determine_player_goal(self, category: str, intent: str, 
                              subject: Optional[str], 
                              conversation_history: List[Dict]) -> str:
        """Determine what the player is trying to achieve."""
        goal_map = {
            'greeting': 'establish_contact',
            'farewell': 'end_conversation',
            'information': 'learn_information',
            'quest_interest': 'find_work',
            'accept_quest': 'accept_quest',
            'decline_quest': 'decline_quest',
            'browse_shop': 'browse_items',
            'ask_price': 'check_price',
            'buy_item': 'purchase_item',
            'sell_item': 'sell_item',
            'confirm_purchase': 'confirm_purchase',
            'craft_item': 'get_item_crafted',
            'repair_item': 'get_item_repaired',
            'training_request': 'learn_skill',
            'buff_request': 'get_buff',
            'acknowledgement': 'respond',
            'confirm': 'confirm',
            'deny': 'deny',
            'clarification': 'get_clarification'
        }
        
        return goal_map.get(intent, 'interact')
    
    def _determine_npc_goal(self, actor_state: Dict, category: str, 
                           conversation_memory: Dict) -> str:
        """Determine what the NPC wants from this conversation."""
        # Default goals based on NPC type
        actor_type = actor_state.get('type', 'npc')
        
        if actor_type == 'shopkeeper':
            return 'sell_items'
        elif actor_type == 'quest_giver':
            return 'offer_quest'
        elif actor_type == 'craftsman':
            return 'provide_service'
        elif actor_type == 'trainer':
            return 'teach_skill'
        else:
            return 'help_player'
    
    def _get_active_quest(self, player_state: Dict) -> Optional[str]:
        """Get the player's active quest if any."""
        quests = player_state.get('quests', [])
        if quests:
            # Return the first active quest
            for quest in quests:
                if quest.get('status') == 'active':
                    return quest.get('id')
        return None
    
    def _get_quest_stage(self, player_state: Dict, active_quest: Optional[str]) -> str:
        """Get the current stage of the active quest."""
        if not active_quest:
            return "none"
        
        quests = player_state.get('quests', [])
        for quest in quests:
            if quest.get('id') == active_quest:
                steps = quest.get('steps', [])
                for step in steps:
                    if step.get('current', 0) < step.get('count', 1):
                        return step.get('description', 'in_progress')
                return 'completion_ready'
        
        return "none"
    
    def _determine_relationship(self, player_state: Dict, 
                               actor_state: Dict) -> str:
        """Determine the relationship between player and NPC."""
        actor_id = actor_state.get('id', '')
        reputation = player_state.get('reputation', {}).get('actors', {}).get(actor_id, 0)
        
        if reputation >= 50:
            return "friendly"
        elif reputation >= 10:
            return "neutral"
        elif reputation >= -10:
            return "indifferent"
        elif reputation >= -50:
            return "unfriendly"
        else:
            return "hostile"
    
    def _get_known_topics(self, player_state: Dict, actor_state: Dict) -> List[str]:
        """Get topics the player has learned from this NPC."""
        actor_id = actor_state.get('id', '')
        known_facts = player_state.get('known_facts', [])
        
        # Filter facts related to this NPC
        # For now, return all known facts (could be filtered by NPC)
        return known_facts
    
    def _determine_facts(self, category: str, intent: str, subject: Optional[str],
                        actor_state: Dict, player_state: Dict,
                        conversation_memory: Dict) -> List[str]:
        """Determine what facts should be communicated in this response."""
        facts = []
        
        # Get NPC knowledge
        knowledge = actor_state.get('knowledge', {})
        
        # If this is an information request, find relevant facts
        if category == 'information' and subject:
            # Search for matching knowledge
            for topic_key, topic_data in knowledge.items():
                if subject.lower() in topic_key.lower() or topic_key.lower() in subject.lower():
                    # Get stages
                    stages = topic_data.get('stages', [])
                    known_facts = player_state.get('known_facts', [])
                    
                    # Find next unrevealed stage
                    for stage in stages:
                        stage_id = stage.get('id', '')
                        if stage_id not in known_facts:
                            # Add facts from this stage
                            facts.extend(stage.get('facts', []))
                            break
        
        # If this is a quest interaction, include quest facts
        elif category == 'quest':
            world_data = actor_state.get('world', {})
            available_quests = world_data.get('available_quests', [])
            
            if intent == 'quest_interest':
                # List available quests
                for quest in available_quests:
                    quest_id = quest.get('id', '')
                    completed = quest_id in player_state.get('completed_quests', [])
                    active = any(q.get('id') == quest_id for q in player_state.get('quests', []))
                    
                    if not completed and not active:
                        facts.append(f"Quest available: {quest.get('name', 'Unknown')}")
        
        # If this is a shop interaction, include shop facts
        elif category == 'shop':
            world_data = actor_state.get('world', {})
            shop_data = world_data.get('shop', {})
            shop_items = shop_data.get('items', [])
            
            if intent == 'browse_shop':
                # List available items
                for item in shop_items[:5]:  # Limit to 5 items
                    facts.append(f"{item.get('name', 'Unknown')}: {item.get('price', 0)} gold")
            
            elif intent in ['ask_price', 'buy_item', 'confirm_purchase']:
                # Find specific item
                if subject:
                    for item in shop_items:
                        if subject.lower() in item.get('name', '').lower():
                            facts.append(f"{item.get('name', 'Unknown')}: {item.get('price', 0)} gold")
                            break
        
        return facts
    
    def _determine_emotion(self, category: str, intent: str, actor_state: Dict,
                          conversation_memory: Dict, relationship: str) -> str:
        """Determine the emotional tone for the response."""
        # Base emotion on relationship
        if relationship == "friendly":
            base_emotion = "friendly"
        elif relationship == "hostile":
            base_emotion = "cold"
        else:
            base_emotion = "neutral"
        
        # Adjust based on category and intent
        if category == 'greeting':
            return "friendly"
        elif category == 'farewell':
            return "neutral"
        elif category == 'quest' and intent == 'accept_quest':
            return "grateful"
        elif category == 'shop' and intent == 'buy_item':
            return "pleased"
        elif category == 'information':
            return "helpful"
        elif intent in ['deny', 'decline_quest']:
            return "disappointed"
        else:
            return base_emotion
    
    def _determine_response_type(self, category: str, intent: str,
                                conversation_memory: Dict) -> str:
        """Determine the type of response to generate."""
        type_map = {
            'greeting': 'greeting',
            'farewell': 'farewell',
            'information': 'informative',
            'quest_interest': 'quest_offer',
            'accept_quest': 'quest_accepted',
            'decline_quest': 'quest_declined',
            'browse_shop': 'shop_catalog',
            'ask_price': 'price_info',
            'buy_item': 'purchase_confirm',
            'sell_item': 'sell_confirm',
            'confirm_purchase': 'purchase_complete',
            'craft_item': 'crafting_service',
            'repair_item': 'repair_service',
            'training_request': 'training_offer',
            'buff_request': 'buff_service',
            'acknowledgement': 'acknowledgement',
            'confirm': 'confirmation',
            'deny': 'denial',
            'clarification': 'clarification'
        }
        
        return type_map.get(intent, 'general')


# Global instance
world_reasoning = WorldReasoningEngine()


def reason_world(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to perform world reasoning.
    
    Args:
        input_data: Input structure with layer1_result, player_state, etc.
    
    Returns:
        Reasoning context with conversation_state, world_state, facts, etc.
    """
    return world_reasoning.reason(input_data)