"""
Conversation Simulator (Layer 2)

Extracted from server/npc_conversation.py
Handles all simulation logic for NPC conversations:
- Shop browsing and purchases
- Quest offering, acceptance, and completion
- Knowledge progression
- Special actions (healing)
- Conversation memory updates

This module NEVER generates dialogue text.
It only returns simulation packets for Layer 3 to narrate.
"""

from typing import Dict, Any, List, Optional
import json
import os


class ConversationSimulator:
    """Simulates NPC conversation interactions."""
    
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
    
    def simulate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate conversation interaction.
        
        Args:
            input_data: {
                "player_state": {},
                "actor_state": {},
                "conversation_memory": {},
                "world_state": {},
                "layer1_result": {
                    "intent": str,
                    "entities": list,
                    "topics": list,
                    "item": str (optional),
                    "topic": str (optional)
                },
                "conversation_state": ConversationState (optional)
            }
        
        Returns:
            Simulation packet (NO dialogue text):
            {
                "action": str,
                "emotion": str,
                "quest_id": str (optional),
                "quest_title": str (optional),
                "quest_description": str (optional),
                "reward_gold": int (optional),
                "reward_items": list (optional),
                "item_name": str (optional),
                "item_price": int (optional),
                "knowledge_topic": str (optional),
                "knowledge_facts": list (optional),
                "shop_items": list (optional),
                "heal_success": bool (optional),
                "heal_amount": int (optional),
                "world_updates": list,
                "memory_updates": dict,
                "reputation_changes": dict,
                "state_updates": dict (optional) - 3-tier state updates
            }
        """
        player_state = input_data.get('player_state', {})
        actor_state = input_data.get('actor_state', {})
        conversation_memory = input_data.get('conversation_memory', {})
        world_state = input_data.get('world_state', {})
        layer1_result = input_data.get('layer1_result', {})
        conversation_state = input_data.get('conversation_state')  # New: 3-tier state
        
        # =========================================================
        # LAYER 1 OUTPUT CONSUMPTION
        # New format: {"category": "...", "intents": [...], "subject": "..."}
        # =========================================================
        
        # Try new format first
        category = layer1_result.get('category', '')
        intents = layer1_result.get('intents', [])
        subject = layer1_result.get('subject')
        
        if category and intents:
            # New format detected
            intent = intents[0]  # Primary intent
            # Store subject for Layer 2 use
            layer1_subject = subject
        else:
            # Fallback to old format for backward compatibility
            intent_candidates = layer1_result.get('intent_candidates', [])
            if intent_candidates:
                intent = intent_candidates[0]['intent']
            else:
                intent = layer1_result.get('intent', 'other')
            layer1_subject = None
        
        # Initialize packet
        packet = {
            'action': 'none',
            'emotion': 'neutral',
            'world_updates': [],
            'memory_updates': {},
            'reputation_changes': {}
        }
        
        # Route to appropriate simulation handler
        if intent == 'buy_item':
            packet = self._simulate_shop_purchase(player_state, actor_state, layer1_result, packet)
        elif intent == 'ask_price':
            packet = self._simulate_shop_purchase(player_state, actor_state, layer1_result, packet)
        elif intent == 'browse_shop':
            packet = self._simulate_shop_browsing(player_state, actor_state, packet)
        elif intent == 'confirm_purchase':
            packet = self._simulate_shop_purchase(player_state, actor_state, layer1_result, packet)
        elif intent == 'sell_item':
            packet = self._simulate_shop_sell(player_state, actor_state, layer1_result, packet)
        elif intent == 'request_information':
            packet = self._simulate_knowledge_sharing(player_state, actor_state, layer1_result, packet)
        elif intent == 'quest_interest':
            packet = self._simulate_quest_interaction(player_state, actor_state, layer1_result, packet)
        elif intent == 'accept_quest':
            packet = self._simulate_quest_acceptance(player_state, actor_state, layer1_result, packet)
        elif intent == 'decline_quest':
            packet['action'] = 'quest_declined'
            packet['emotion'] = 'neutral'
        elif intent == 'hello':
            packet['action'] = 'greeting'
            packet['emotion'] = 'friendly'
        elif intent == 'goodbye':
            packet['action'] = 'farewell'
            packet['emotion'] = 'neutral'
        elif intent == 'craft_item':
            packet = self._simulate_crafting(player_state, actor_state, layer1_result, packet)
        elif intent == 'repair_item':
            packet = self._simulate_repair(player_state, actor_state, layer1_result, packet)
        elif intent == 'training_request':
            packet = self._simulate_training(player_state, actor_state, layer1_result, packet)
        elif intent == 'buff_request':
            packet = self._simulate_buff(player_state, actor_state, layer1_result, packet)
        elif intent in ['acknowledgement', 'confirm', 'deny', 'clarification']:
            packet = self._simulate_general_conversation(player_state, actor_state, conversation_memory, packet)
        
        # Update conversation memory
        packet['memory_updates'] = self._update_conversation_memory(
            player_state, actor_state, conversation_memory, layer1_result, packet
        )
        
        return packet
    
    def _simulate_shop_purchase(self, player_state: Dict, actor_state: Dict, 
                                layer1_result: Dict, packet: Dict) -> Dict:
        """Simulate shop purchase interaction."""
        item_name = layer1_result.get('item', '').lower()
        
        # Get shop data from actor
        world_data = actor_state.get('world', {})
        shop_data = world_data.get('shop', {})
        shop_items = shop_data.get('items', [])
        
        # Find matching item
        wanted_item = None
        for item in shop_items:
            if item_name in item.get('name', '').lower():
                wanted_item = item
                break
        
        if not wanted_item:
            packet['action'] = 'shop_item_not_found'
            packet['emotion'] = 'neutral'
            return packet
        
        # Check if item is secret/quest-gated
        if wanted_item.get('secret', False):
            quest_required = wanted_item.get('quest_required', '')
            if quest_required:
                packet['action'] = 'shop_item_quest_gated'
                packet['quest_required'] = quest_required
                packet['emotion'] = 'apologetic'
            else:
                packet['action'] = 'shop_item_unavailable'
                packet['emotion'] = 'apologetic'
            return packet
        
        # Check if player has enough coins
        price = wanted_item.get('price', 0)
        player_coins = player_state.get('coins', 0)
        
        if player_coins < price:
            packet['action'] = 'shop_insufficient_funds'
            packet['item_name'] = wanted_item.get('name', '')
            packet['item_price'] = price
            packet['emotion'] = 'apologetic'
            return packet
        
        # Find item ID from visible_for_sale
        item_name_display = wanted_item.get('name', '')
        item_id = None
        visible_ids = actor_state.get('shop', {}).get('visible_for_sale', [])
        
        # Try to match by name
        for vid in visible_ids:
            # This would need access to items_db - for now use name-based matching
            if item_name_display.lower().replace(' ', '_') == vid.lower():
                item_id = vid
                break
        
        if not item_id:
            item_id = item_name_display.lower().replace(' ', '_')
        
        # Successful purchase
        packet['action'] = 'shop_purchase_success'
        packet['item_id'] = item_id
        packet['item_name'] = item_name_display
        packet['item_price'] = price
        packet['emotion'] = 'happy'
        
        # World updates (state changes)
        packet['world_updates'] = [
            {
                'type': 'coins_change',
                'player_id': player_state.get('id', ''),
                'amount': -price
            },
            {
                'type': 'inventory_add',
                'player_id': player_state.get('id', ''),
                'item_id': item_id,
                'quantity': 1
            }
        ]
        
        return packet
    
    def _simulate_knowledge_sharing(self, player_state: Dict, actor_state: Dict,
                                    layer1_result: Dict, packet: Dict) -> Dict:
        """Simulate knowledge sharing interaction."""
        # Get topics from Layer 1 (both subjects and topics)
        subjects = layer1_result.get('subjects', [])
        topics = layer1_result.get('topics', [])
        
        # Get knowledge from actor
        knowledge = actor_state.get('knowledge', {})
        
        # Find matching topic (check both subjects and topics from Layer 1)
        matched_topic = None
        matched_topic_data = None
        
        # Search through all provided topics/subjects
        search_terms = subjects + topics
        for search_term in search_terms:
            search_normalized = search_term.lower().replace('_', ' ')
            for topic_key, topic_data in knowledge.items():
                topic_key_normalized = topic_key.lower().replace('_', ' ')
                if topic_key_normalized in search_normalized or search_normalized in topic_key_normalized:
                    matched_topic = topic_key
                    matched_topic_data = topic_data
                    break
            if matched_topic:
                break
        
        if not matched_topic or not matched_topic_data:
            packet['action'] = 'knowledge_no_info'
            packet['emotion'] = 'neutral'
            return packet
        
        # Get stages
        stages = matched_topic_data.get('stages', [])
        if not stages:
            packet['action'] = 'knowledge_no_info'
            packet['emotion'] = 'neutral'
            return packet
        
        # Check what has been revealed to player
        player_id = player_state.get('id', '')
        known_facts = player_state.get('known_facts', [])
        
        # Find next unrevealed stage
        next_stage = None
        for stage in stages:
            stage_id = stage.get('id', '')
            if stage_id not in known_facts:
                next_stage = stage
                break
        
        if not next_stage:
            # All stages revealed
            packet['action'] = 'knowledge_all_revealed'
            packet['topic'] = matched_topic
            packet['emotion'] = 'neutral'
            return packet
        
        # Check visibility conditions
        visibility = next_stage.get('visibility', 'normal')
        conditions = next_stage.get('conditions', [])
        
        # For now, reveal eager and normal stages immediately
        # Hidden stages would need condition checking
        if visibility == 'hidden':
            packet['action'] = 'knowledge_locked'
            packet['topic'] = matched_topic
            packet['emotion'] = 'cautious'
            return packet
        
        # Reveal the knowledge - provide COMPLETE data
        facts = next_stage.get('facts', [])
        stage_id = next_stage.get('id', '')
        
        packet['action'] = 'share_information'
        packet['topic'] = matched_topic
        packet['subject'] = subjects[0] if subjects else ''
        packet['facts'] = facts  # ALL facts from this stage
        packet['emotion'] = 'helpful'
        
        # Memory update
        packet['memory_updates'] = {
            'known_facts_add': [stage_id]
        }
        
        return packet
    
    def _simulate_quest_interaction(self, player_state: Dict, actor_state: Dict,
                                    layer1_result: Dict, packet: Dict) -> Dict:
        """Simulate quest offering/acceptance/completion."""
        player_quests = player_state.get('quests', [])
        completed_quests = player_state.get('completed_quests', [])
        
        # Get available quests from actor
        world_data = actor_state.get('world', {})
        available_quests = world_data.get('available_quests', [])
        
        # Check if player is asking about a specific quest
        quest_name = layer1_result.get('topic', '').lower()
        
        # Find matching quest (only if a specific quest was mentioned)
        matched_quest = None
        if quest_name:  # Only search if a quest name was actually mentioned
            for quest_def in available_quests:
                quest_name_def = quest_def.get('name', '').lower()
                if quest_name in quest_name_def or quest_name_def in quest_name:
                    matched_quest = quest_def
                    break
        
        if not matched_quest:
            # No specific quest mentioned, list available quests
            available = []
            for quest_def in available_quests:
                quest_id = quest_def.get('id', '')
                prerequisites = quest_def.get('prerequisites', [])
                
                # Check prerequisites
                prereqs_met = all(p in completed_quests for p in prerequisites)
                
                # Check if already active or completed
                already_active = any(q.get('id') == quest_id for q in player_quests)
                already_completed = quest_id in completed_quests
                
                if prereqs_met and not already_active and not already_completed:
                    available.append(quest_def)
            
            if available:
                packet['action'] = 'quest_list_available'
                packet['available_quests'] = [
                    {
                        'id': q.get('id', ''),
                        'name': q.get('name', ''),
                        'description': q.get('description', '')
                    }
                    for q in available
                ]
                packet['emotion'] = 'helpful'
            else:
                packet['action'] = 'quest_none_available'
                packet['emotion'] = 'neutral'
            
            return packet
        
        # Specific quest found
        quest_id = matched_quest.get('id', '')
        prerequisites = matched_quest.get('prerequisites', [])
        
        # Check prerequisites
        prereqs_met = all(p in completed_quests for p in prerequisites)
        
        if not prereqs_met:
            packet['action'] = 'quest_prerequisites_not_met'
            packet['quest_id'] = quest_id
            packet['emotion'] = 'apologetic'
            return packet
        
        # Check if already active
        already_active = any(q.get('id') == quest_id for q in player_quests)
        if already_active:
            packet['action'] = 'quest_already_active'
            packet['quest_id'] = quest_id
            packet['emotion'] = 'neutral'
            return packet
        
        # Check if already completed
        if quest_id in completed_quests:
            packet['action'] = 'quest_already_completed'
            packet['quest_id'] = quest_id
            packet['emotion'] = 'proud'
            return packet
        
        # Offer quest
        packet['action'] = 'offer_quest'
        packet['quest_id'] = quest_id
        packet['quest_title'] = matched_quest.get('name', '')
        packet['quest_description'] = matched_quest.get('description', '')
        packet['reward_gold'] = matched_quest.get('reward_gold', 0)
        packet['reward_items'] = matched_quest.get('reward_items', [])
        packet['emotion'] = 'hopeful'
        
        return packet
    
    def _simulate_shop_browsing(self, player_state: Dict, actor_state: Dict, packet: Dict) -> Dict:
        """Simulate shop browsing interaction."""
        world_data = actor_state.get('world', {})
        shop_data = world_data.get('shop', {})
        shop_items = shop_data.get('items', [])
        
        if not shop_items:
            packet['action'] = 'shop_empty'
            packet['emotion'] = 'neutral'
            return packet
        
        # Return list of available items
        packet['action'] = 'shop_browse'
        packet['shop_items'] = [
            {
                'name': item.get('name', ''),
                'price': item.get('price', 0),
                'description': item.get('description', '')
            }
            for item in shop_items
        ]
        packet['emotion'] = 'helpful'
        
        return packet
    
    def _simulate_crafting(self, player_state: Dict, actor_state: Dict, 
                           layer1_result: Dict, packet: Dict) -> Dict:
        """Simulate crafting interaction - expose existing crafting data."""
        # Get recipe from Layer 1
        recipe_id = layer1_result.get('recipe', '')
        
        if not recipe_id:
            packet['action'] = 'crafting_no_recipe'
            packet['emotion'] = 'neutral'
            return packet
        
        # Load recipe data from crafting system
        try:
            from engine.recipe_manager import RecipeManager
            recipe_manager = RecipeManager()
            recipe = recipe_manager.get_recipe(recipe_id)
        except Exception:
            # If recipe manager unavailable, use basic data
            recipe = None
        
        # Get recipe name
        if recipe:
            recipe_name = recipe.get('name', recipe_id.replace('_', ' ').title())
        else:
            recipe_name = recipe_id.replace('_', ' ').title()
        
        # Get materials required (inputs)
        if recipe and recipe.get('inputs'):
            materials_required = [
                {"item_id": inp.get('item', ''), "quantity": inp.get('quantity', 1)}
                for inp in recipe['inputs']
            ]
        else:
            materials_required = layer1_result.get('materials', [])
        
        # Build packet with ALL available data
        packet['action'] = 'craft_item'
        packet['recipe_id'] = recipe_id
        packet['recipe_name'] = recipe_name
        packet['materials_required'] = materials_required
        
        # Add outputs if available
        if recipe and recipe.get('outputs'):
            packet['outputs'] = [
                {"item_id": out.get('item', ''), "quantity": out.get('quantity', 1)}
                for out in recipe['outputs']
            ]
        
        # Add duration if available
        if recipe and recipe.get('duration_ticks'):
            packet['duration_ticks'] = recipe['duration_ticks']
        
        # Add technique and station if available
        if recipe:
            try:
                from engine.recipe_manager import get_discipline_for_recipe
                discipline = get_discipline_for_recipe(recipe_id)
                if discipline:
                    packet['technique_required'] = discipline.get('technique', '')
                    packet['station_required'] = discipline.get('station', '')
            except Exception:
                pass
        
        packet['emotion'] = 'focused'
        
        return packet
    
    def _simulate_repair(self, player_state: Dict, actor_state: Dict,
                         layer1_result: Dict, packet: Dict) -> Dict:
        """Simulate repair interaction."""
        item_name = layer1_result.get('item', '')
        
        # Basic repair packet - repair system not fully implemented
        packet['action'] = 'repair_item'
        packet['item_name'] = item_name.replace('_', ' ').title() if item_name else 'item'
        packet['repair_cost'] = 10  # Default cost
        packet['emotion'] = 'focused'
        
        return packet
    
    def _simulate_shop_sell(self, player_state: Dict, actor_state: Dict,
                            layer1_result: Dict, packet: Dict) -> Dict:
        """Simulate shop sell interaction."""
        item_name = layer1_result.get('subject', '')
        
        # Basic sell packet - sell system not fully implemented
        packet['action'] = 'shop_sell'
        packet['item_name'] = item_name if item_name else 'item'
        packet['emotion'] = 'neutral'
        
        return packet
    
    def _simulate_quest_acceptance(self, player_state: Dict, actor_state: Dict,
                                   layer1_result: Dict, packet: Dict) -> Dict:
        """Simulate quest acceptance."""
        # Get the quest that was offered
        world_data = actor_state.get('world', {})
        available_quests = world_data.get('available_quests', [])
        
        # For now, just return acceptance packet
        # Layer 2 will need to track which quest was offered
        packet['action'] = 'quest_accept'
        packet['emotion'] = 'happy'
        
        return packet
    
    def _simulate_training(self, player_state: Dict, actor_state: Dict,
                           layer1_result: Dict, packet: Dict) -> Dict:
        """Simulate training request."""
        subject = layer1_result.get('subject', '')
        
        # Basic training packet - training system not fully implemented
        packet['action'] = 'training_request'
        packet['training_subject'] = subject if subject else 'general'
        packet['emotion'] = 'helpful'
        
        return packet
    
    def _simulate_buff(self, player_state: Dict, actor_state: Dict,
                       layer1_result: Dict, packet: Dict) -> Dict:
        """Simulate buff request."""
        subject = layer1_result.get('subject', '')
        
        # Basic buff packet - buff system not fully implemented
        packet['action'] = 'buff_request'
        packet['buff_subject'] = subject if subject else 'general'
        packet['emotion'] = 'helpful'
        
        return packet
    
    def _simulate_general_conversation(self, player_state: Dict, actor_state: Dict,
                                       conversation_memory: Dict, packet: Dict) -> Dict:
        """Simulate general conversation."""
        packet['action'] = 'general_chat'
        packet['emotion'] = 'neutral'
        return packet
    
    def _simulate_childish_behavior(self, player_state: Dict, actor_state: Dict,
                                    conversation_memory: Dict, packet: Dict) -> Dict:
        """Simulate NPC reaction to childish behavior."""
        # Track warnings in conversation memory
        memory_key = f"{player_state.get('id', '')}_{actor_state.get('id', '')}"
        warnings = conversation_memory.get('childish_warnings', 0)
        
        warnings += 1
        
        if warnings >= 3:
            packet['action'] = 'childish_end_conversation'
            packet['emotion'] = 'annoyed'
        else:
            packet['action'] = 'childish_warning'
            packet['emotion'] = 'annoyed'
        
        packet['memory_updates'] = {
            'childish_warnings': warnings
        }
        
        return packet
    
    def _update_conversation_memory(self, player_state: Dict, actor_state: Dict,
                                    conversation_memory: Dict, layer1_result: Dict,
                                    packet: Dict) -> Dict:
        """Update conversation memory based on interaction."""
        # Start with any existing memory updates from the simulation
        memory_updates = packet.get('memory_updates', {}).copy()
        
        # Initialize memory if needed
        if not conversation_memory:
            memory_updates['initialized'] = True
            memory_updates['history'] = []
            memory_updates['state'] = 'general'
            if 'childish_warnings' not in memory_updates:
                memory_updates['childish_warnings'] = 0
        
        # Add to history
        player_text = layer1_result.get('message', '')
        if player_text:
            memory_updates['history_append'] = {
                'speaker': 'player',
                'text': player_text
            }
        
        # Update state based on action (only if not already set by simulation)
        action = packet.get('action', '')
        if 'state' not in memory_updates and action in ['shop_purchase_success', 'offer_quest', 'knowledge_reveal']:
            memory_updates['state'] = action
        
        return memory_updates
    
    def process_quest_completion(self, quest_id: str, player_state: Dict, 
                                 world_state: Dict) -> Dict:
        """
        Process quest completion.
        
        Args:
            quest_id: Quest ID to complete
            player_state: Player's current state
            world_state: Current world state
        
        Returns:
            Simulation packet with completion results
        """
        packet = {
            'action': 'quest_complete',
            'quest_id': quest_id,
            'world_updates': [],
            'memory_updates': {},
            'reputation_changes': {}
        }
        
        # Get quest definition
        quest_def = self.quest_definitions.get(quest_id)
        if not quest_def:
            packet['action'] = 'quest_complete_failed'
            packet['error'] = 'Quest not found'
            return packet
        
        # Calculate rewards
        reward_gold = quest_def.get('reward_gold', 0)
        reward_items = quest_def.get('reward_items', [])
        
        # World updates
        if reward_gold > 0:
            packet['world_updates'].append({
                'type': 'coins_change',
                'player_id': player_state.get('id', ''),
                'amount': reward_gold
            })
        
        for item_id in reward_items:
            packet['world_updates'].append({
                'type': 'inventory_add',
                'player_id': player_state.get('id', ''),
                'item_id': item_id,
                'quantity': 1
            })
        
        # Mark quest as completed
        packet['world_updates'].append({
            'type': 'quest_complete',
            'player_id': player_state.get('id', ''),
            'quest_id': quest_id
        })
        
        # Reputation changes
        reputation_changes = quest_def.get('reputation_changes', {})
        if reputation_changes:
            packet['reputation_changes'] = reputation_changes
        
        packet['emotion'] = 'proud'
        
        return packet
    
    def process_heal(self, player_state: Dict, actor_state: Dict, 
                     world_state: Dict) -> Dict:
        """
        Process heal action.
        
        Args:
            player_state: Player's current state
            actor_state: NPC's current state
            world_state: Current world state
        
        Returns:
            Simulation packet with heal results
        """
        packet = {
            'action': 'heal',
            'world_updates': [],
            'memory_updates': {}
        }
        
        # Check if actor can heal
        conversation = actor_state.get('conversation', {})
        topics = conversation.get('topics', {})
        
        # For now, simple heal logic
        # In future, check if actor has heal capability
        current_hp = player_state.get('hp', 0)
        max_hp = player_state.get('max_hp', 100)
        
        if current_hp >= max_hp:
            packet['heal_success'] = False
            packet['heal_amount'] = 0
            packet['emotion'] = 'neutral'
            packet['message'] = 'already_at_full_health'
        else:
            heal_amount = max_hp - current_hp
            packet['heal_success'] = True
            packet['heal_amount'] = heal_amount
            packet['emotion'] = 'helpful'
            
            # World update
            packet['world_updates'].append({
                'type': 'hp_change',
                'player_id': player_state.get('id', ''),
                'amount': heal_amount
            })
        
        return packet


# Global simulator instance
conversation_simulator = ConversationSimulator()


def simulate_conversation(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to simulate conversation.
    
    Args:
        input_data: Input structure with player_state, actor_state, etc.
    
    Returns:
        Simulation packet (NO dialogue text)
    """
    return conversation_simulator.simulate(input_data)


def process_quest_completion(quest_id: str, player_state: Dict, 
                             world_state: Dict) -> Dict[str, Any]:
    """
    Convenience function to process quest completion.
    
    Args:
        quest_id: Quest ID to complete
        player_state: Player's current state
        world_state: Current world state
    
    Returns:
        Simulation packet
    """
    return conversation_simulator.process_quest_completion(quest_id, player_state, world_state)


def process_heal(player_state: Dict, actor_state: Dict, 
                 world_state: Dict) -> Dict[str, Any]:
    """
    Convenience function to process heal action.
    
    Args:
        player_state: Player's current state
        actor_state: NPC's current state
        world_state: Current world state
    
    Returns:
        Simulation packet
    """
    return conversation_simulator.process_heal(player_state, actor_state, world_state)