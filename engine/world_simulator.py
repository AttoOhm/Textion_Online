"""
Layer 2: World Simulation Engine

SINGLE RESPONSIBILITY: Simulate world state changes based on player intent.

Layer 2 does NOT:
- Create conversation topics
- Create conversation modes
- Create conversation stages
- Generate NPC reasoning/thoughts
- Rank intents
- Select between intents

Layer 2 ONLY:
- Receives category + primary_intent + secondary_intent from Layer 1
- Checks game data (NPC inventory, quests, prices, etc.)
- Determines what CAN happen in the world
- Returns a packet describing the result

Layer 2 is deterministic - no LLM calls.
"""

from typing import Dict, Any, List, Optional
import json
import os


class WorldSimulator:
    """Simulates world state based on player intent."""
    
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
    
    def simulate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate world state based on player intent.
        
        Args:
            input_data: {
                "player_message": str,
                "conversation_history": List[Dict],
                "conversation_memory": Dict,
                "npc_data": Dict,
                "player_state": Dict,
                "world_state": Dict,
                "layer1_understanding": Dict  # From Layer 1
            }
        
        Returns:
            Packet describing what happened:
            {
                "action": "shop_browse",
                "visible_items": [...],
                "npc_emotion": "helpful"
            }
        """
        player_message = input_data.get('player_message', '')
        conversation_history = input_data.get('conversation_history', [])
        conversation_memory = input_data.get('conversation_memory', {})
        npc_data = input_data.get('npc_data', {})
        player_state = input_data.get('player_state', {})
        world_state = input_data.get('world_state', {})
        layer1 = input_data.get('layer1_understanding', {})
        
        # Get category and intents from Layer 1
        category = layer1.get('category', 'General')
        primary_intent = layer1.get('primary_intent', 'general_chat')
        secondary_intent = layer1.get('secondary_intent', primary_intent)
        
        # Get entities from Layer 1
        entities = layer1.get('entities', [])
        
        # Get player attitude and emotion from Layer 1
        player_attitude = layer1.get('attitude', 'neutral')
        player_emotion = layer1.get('emotion', 'neutral')
        
        # =========================================================
        # WORLD SIMULATION - Determine what CAN happen
        # =========================================================
        
        # Route based on category and primary intent
        if category == 'General':
            return self._handle_general(npc_data, player_state, primary_intent)
        
        elif category == 'Information':
            return self._handle_information(npc_data, player_state, entities, layer1)
        
        elif category == 'Quest':
            return self._handle_quest(npc_data, player_state, primary_intent, conversation_memory, layer1)
        
        elif category == 'Commerce':
            # Check if this is a confirmation of a pending purchase
            primary_intent = self._check_pending_purchase_confirmation(
                primary_intent, conversation_memory, player_message
            )
            return self._handle_commerce(npc_data, player_state, primary_intent, entities, conversation_memory, layer1)
        
        elif category == 'Training':
            return self._handle_training(npc_data, player_state, primary_intent)
        
        elif category == 'Services':
            return self._handle_services(npc_data, player_state, primary_intent, entities)
        
        else:
            return self._handle_general(npc_data, player_state, 'general_chat')
    
    def _handle_general(self, npc_data: Dict, player_state: Dict, intent: str) -> Dict:
        """Handle General category intents."""
        if intent == 'greeting':
            return {
                "action": "greeting",
                "npc_emotion": "friendly"
            }
        elif intent == 'farewell':
            return {
                "action": "farewell",
                "npc_emotion": "neutral"
            }
        else:
            return {
                "action": "general_chat",
                "npc_emotion": "neutral"
            }
    
    def _handle_information(self, npc_data: Dict, player_state: Dict, 
                           entities: List[Dict], layer1: Dict = None) -> Dict:
        """Handle Information category intents."""
        knowledge = npc_data.get('knowledge', {})
        
        # Get subject from Layer 1
        subject = layer1.get('subject', '') if layer1 else ''
        
        # Check if this information request completes any active quest
        if subject:
            active_quests = player_state.get('quests', [])
            completed_quests = player_state.get('completed_quests', [])
            
            for quest in active_quests:
                quest_id = quest.get('id', '')
                # Check if quest is already completed (completed_quests is list of dicts)
                if any(q.get('id') == quest_id for q in completed_quests):
                    continue
                
                # Load quest definition
                quest_def = self.quest_definitions.get(quest_id)
                if not quest_def:
                    continue
                
                # Check if this NPC can complete this quest
                completion_npc = quest_def.get('completion_npc', '')
                completion_topic = quest_def.get('completion_topic', '')
                
                if completion_npc and completion_topic:
                    # Check if talking to the right NPC about the right topic
                    if (npc_data.get('id') == completion_npc or 
                        npc_data.get('id') in quest_def.get('participants', [])):
                        # Check if subject matches completion topic
                        if (subject.lower() == completion_topic.lower() or
                            completion_topic.lower() in subject.lower() or
                            subject.lower() in completion_topic.lower()):
                            # Complete the quest!
                            return {
                                "action": "quest_complete",
                                "quest_id": quest_id,
                                "quest_title": quest_def.get('title', quest_def.get('name', 'Unknown Quest')),
                                "rewards": quest_def.get('rewards', {}),
                                "npc_emotion": "pleased",
                                "world_actions": [
                                    {
                                        "type": "quest_complete",
                                        "quest_id": quest_id
                                    }
                                ]
                            }
        
        if entities:
            # Handle both dict and string entities
            entity = entities[0]
            if isinstance(entity, dict):
                topic = entity.get('id', '')
            else:
                topic = str(entity)
            
            # Check if NPC knows about this topic
            for topic_key in knowledge.keys():
                if topic.lower() in topic_key.lower() or topic_key.lower() in topic.lower():
                    return {
                        "action": "share_information",
                        "topic": topic_key,
                        "npc_emotion": "helpful"
                    }
        
        return {
            "action": "knowledge_no_info",
            "npc_emotion": "apologetic"
        }
    
    def _handle_quest(self, npc_data: Dict, player_state: Dict, 
                     primary_intent: str, conversation_memory: Dict, 
                     layer1: Dict = None) -> Dict:
        """Handle Quest category intents."""
        world_data = npc_data.get('world', {})
        available_quests = world_data.get('available_quests', [])
        completed_quests = player_state.get('completed_quests', [])
        active_quests = player_state.get('quests', [])
        
        # Get subject from Layer 1 to match specific quest
        subject = layer1.get('subject', '') if layer1 else ''
        
        # Check for explicit quest finish
        if primary_intent in ['quest_finish']:
            # Find first active quest that can be completed by this NPC
            for quest in active_quests:
                quest_id = quest.get('id', '')
                # Check if quest is already completed (completed_quests is list of dicts)
                if any(q.get('id') == quest_id for q in completed_quests):
                    continue
                
                # Load quest definition
                quest_def = self.quest_definitions.get(quest_id)
                if not quest_def:
                    continue
                
                # Check if this NPC can complete this quest
                completion_npc = quest_def.get('completion_npc', '')
                if completion_npc and npc_data.get('id') == completion_npc:
                    # Complete the quest!
                    return {
                        "action": "quest_complete",
                        "quest_id": quest_id,
                        "quest_title": quest_def.get('title', quest_def.get('name', 'Unknown Quest')),
                        "rewards": quest_def.get('rewards', {}),
                        "npc_emotion": "pleased",
                        "world_actions": [
                            {
                                "type": "quest_complete",
                                "quest_id": quest_id
                            }
                        ]
                    }
        
        # Check for quest completion (talk to NPC about topic)
        if primary_intent in ['quest_information', 'ask_npc', 'ask_creature'] and subject:
            # Check if any active quest can be completed by talking to this NPC about this topic
            for quest in active_quests:
                quest_id = quest.get('id', '')
                # Check if quest is already completed (completed_quests is list of dicts)
                if any(q.get('id') == quest_id for q in completed_quests):
                    continue
                
                # Load quest definition to check completion conditions
                quest_def = self.quest_definitions.get(quest_id)
                if not quest_def:
                    continue
                
                # Check if this NPC can complete this quest
                completion_npc = quest_def.get('completion_npc', '')
                completion_topic = quest_def.get('completion_topic', '')
                
                if completion_npc and completion_topic:
                    # Check if talking to the right NPC about the right topic
                    if (npc_data.get('id') == completion_npc or 
                        npc_data.get('id') in quest_def.get('participants', [])):
                        # Check if subject matches completion topic
                        if (subject.lower() == completion_topic.lower() or
                            completion_topic.lower() in subject.lower() or
                            subject.lower() in completion_topic.lower()):
                            # Complete the quest!
                            return {
                                "action": "quest_complete",
                                "quest_id": quest_id,
                                "quest_title": quest_def.get('title', quest_def.get('name', 'Unknown Quest')),
                                "rewards": quest_def.get('rewards', {}),
                                "npc_emotion": "pleased",
                                "world_actions": [
                                    {
                                        "type": "quest_complete",
                                        "quest_id": quest_id
                                    }
                                ]
                            }
        
        # Check if this is a confirmation/accept
        if primary_intent in ['quest_accept']:
            matched_quest = None
            
            # Try to find quest by subject first
            if subject:
                for quest in available_quests:
                    quest_id = quest.get('id', '')
                    quest_name = quest.get('name', '').lower()
                    if subject.lower() in quest_name or quest_name in subject.lower():
                        # Check prerequisites
                        prerequisites = quest.get('prerequisites', [])
                        completed_quest_ids = [q.get("id") if isinstance(q, dict) else q for q in completed_quests]
                        prereqs_met = all(p in completed_quest_ids for p in prerequisites)
                        if prereqs_met and quest_id not in completed_quests and \
                           not any(q.get('id') == quest_id for q in active_quests):
                            matched_quest = quest
                            break
            
            # If no match by subject, check for pending quest offer in conversation memory
            if not matched_quest:
                pending_quest = conversation_memory.get('pending_quest')
                if pending_quest:
                    # Find the quest that was offered
                    for quest in available_quests:
                        if quest.get('id') == pending_quest:
                            # Double-check prerequisites
                            prerequisites = quest.get('prerequisites', [])
                            completed_quest_ids = [q.get("id") if isinstance(q, dict) else q for q in completed_quests]
                            prereqs_met = all(p in completed_quest_ids for p in prerequisites)
                            if prereqs_met:
                                matched_quest = quest
                            break
            
            # If still no match, use first available (which should already be filtered by prerequisites)
            if not matched_quest:
                for quest in available_quests:
                    quest_id = quest.get('id', '')
                    if quest_id not in completed_quests and \
                       not any(q.get('id') == quest_id for q in active_quests):
                        matched_quest = quest
                        break
            
            if matched_quest:
                quest_id = matched_quest.get('id', '')
                # Accept the quest - add to player state via world_actions
                return {
                    "action": "offer_quest",
                    "quest_id": quest_id,
                    "quest_title": matched_quest.get('name', 'Unknown Quest'),
                    "quest_description": matched_quest.get('description', ''),
                    "rewards": matched_quest.get('rewards', {}),
                    "npc_emotion": "hopeful",
                    "world_actions": [
                        {
                            "type": "offer_quest",
                            "quest_id": quest_id,
                            "quest_name": matched_quest.get('name', 'Unknown Quest')
                        }
                    ]
                }
        
        # Otherwise, list available quests (only those with prerequisites met)
        available = []
        print(f"[QUEST] Checking available quests. Completed: {completed_quests}, Active: {[q.get('id') for q in active_quests]}")
        
        for quest in available_quests:
            quest_id = quest.get('id', '')
            quest_name = quest.get('name', 'Unknown')
            prerequisites = quest.get('prerequisites', [])
            
            # Skip if already completed or active
            completed_quest_ids = [q.get('id') if isinstance(q, dict) else q for q in completed_quests]
            if quest_id in completed_quest_ids or \
               any(q.get('id') == quest_id for q in active_quests):
                print(f"[QUEST] Skipping {quest_id} - already completed or active")
                continue
            
            # Check prerequisites
            completed_quest_ids = [q.get("id") if isinstance(q, dict) else q for q in completed_quests]
            prereqs_met = all(p in completed_quest_ids for p in prerequisites)
            print(f"[QUEST] {quest_id}: prereqs={prerequisites}, met={prereqs_met}")
            
            if prereqs_met:
                available.append({
                    "quest_id": quest_id,
                    "quest_title": quest_name,
                    "quest_summary": quest.get('description', '')[:100]
                })
        
        print(f"[QUEST] Available quests: {[q['quest_title'] for q in available]}")
        
        if available:
            # Only show ONE quest at a time for proper conversation flow
            # The NPC offers one quest, player accepts/declines, then we move to next
            first_quest = available[0]
            pending_quest_id = first_quest.get('quest_id')
            
            return {
                "action": "quest_list_available",
                "available_quests": [first_quest],  # Only return ONE quest
                "npc_emotion": "helpful",
                "memory_updates": {
                    "pending_quest": pending_quest_id,
                    "quest_list_index": 0,
                    "all_available_quests": available  # Store full list for auto-advancement
                }
            }
        else:
            return {
                "action": "no_quests_available",
                "npc_emotion": "neutral"
            }
    
    def _check_pending_purchase_confirmation(self, primary_intent: str, 
                                             conversation_memory: Dict, 
                                             player_message: str) -> str:
        """Check if player is confirming a pending purchase."""
        # Check if there's a pending purchase
        pending = conversation_memory.get('pending_purchase')
        
        # If already confirming, don't change
        if primary_intent == 'confirm_purchase':
            print(f"[PENDING_PURCHASE] Already confirming, keeping intent")
            return primary_intent
        
        # Check if message looks like a direct purchase (e.g., "i'll buy X for Y gold")
        # This handles cases where there's no pending purchase but player is clearly trying to buy
        message_lower = player_message.lower()
        direct_purchase_patterns = [
            "i'll buy", "i will buy", "i'll take", "i will take",
            "i'll get", "i will get", "i want to buy", "i want to purchase"
        ]
        for pattern in direct_purchase_patterns:
            if pattern in message_lower:
                print(f"[PENDING_PURCHASE] Detected direct purchase: '{pattern}' in '{player_message}'")
                print(f"[PENDING_PURCHASE] Treating as confirm_purchase")
                return 'confirm_purchase'
        
        # If there's a pending purchase, check for confirmation patterns
        if pending:
            print(f"[PENDING_PURCHASE] Found pending purchase: {pending}")
            confirmation_patterns = [
                "yes", "yeah", "yep", "sure", "okay", "ok", "alright",
                "here you go", "deal", "agreed", "sounds good"
            ]
            for pattern in confirmation_patterns:
                if pattern in message_lower:
                    print(f"[PENDING_PURCHASE] Detected confirmation: '{pattern}' in '{player_message}'")
                    print(f"[PENDING_PURCHASE] Pending item: {pending.get('item_name')} for {pending.get('item_price')} gold")
                    return 'confirm_purchase'
            
            print(f"[PENDING_PURCHASE] No confirmation pattern found in '{player_message}'")
        else:
            print(f"[PENDING_PURCHASE] No pending purchase found in memory")
        
        return primary_intent
    
    def _handle_commerce(self, npc_data: Dict, player_state: Dict, 
                        primary_intent: str, entities: List[Dict], 
                        conversation_memory: Dict, layer1: Dict = None) -> Dict:
        """Handle Commerce category intents."""
        world_data = npc_data.get('world', {})
        shop_data = world_data.get('shop', {})
        shop_items = shop_data.get('items', [])
        
        if primary_intent == 'browse_shop':
            # List all items
            if not shop_items:
                return {
                    "action": "shop_empty",
                    "npc_emotion": "apologetic"
                }
            
            # Categorize items for better responses
            weapons = []
            tools = []
            materials = []
            recipes = []
            other = []
            
            for item in shop_items:
                name = item.get('name', item.get('item_name', 'Unknown'))
                category = item.get('category', 'other')
                
                item_info = {"name": name, "price": item.get('price', 0)}
                
                if 'recipe' in name.lower() or category == 'recipe':
                    recipes.append(item_info)
                elif 'sword' in name.lower() or 'axe' in name.lower() or 'dagger' in name.lower() or 'hammer' in name.lower() or category == 'weapon':
                    weapons.append(item_info)
                elif 'pickaxe' in name.lower() or 'hatchet' in name.lower() or 'tool' in name.lower() or category == 'tool':
                    tools.append(item_info)
                elif 'ingot' in name.lower() or 'plank' in name.lower() or category == 'material':
                    materials.append(item_info)
                else:
                    other.append(item_info)
            
            return {
                "action": "shop_browse",
                "shop_categories": {
                    "weapons": weapons,
                    "tools": tools,
                    "materials": materials,
                    "recipes": recipes,
                    "other": other
                },
                "npc_emotion": "helpful"
            }
        
        elif primary_intent == 'ask_price':
            # Find specific item price
            if entities:
                entity = entities[0]
                entity_id = entity.get('id', '') if isinstance(entity, dict) else str(entity)
                entity_id = entity_id.lower()
                for item in shop_items:
                    item_name = item.get('name', item.get('item_name', '')).lower()
                    if entity_id in item_name:
                        return {
                            "action": "shop_item_price",
                            "item_name": item.get('name', item.get('item_name', 'Unknown')),
                            "item_price": item.get('price', 0),
                            "npc_emotion": "helpful"
                        }
            
            return {
                "action": "shop_item_not_found",
                "requested_item": entities[0].get('id', 'item') if entities and isinstance(entities[0], dict) else str(entities[0]) if entities else 'item',
                "npc_emotion": "apologetic"
            }
        
        elif primary_intent in ['buy_item', 'confirm_purchase']:
            # Buy item - execute immediately, no confirmation needed
            is_confirmation = (primary_intent == 'confirm_purchase')
            
            # Find requested item - try entities first, then fall back to subject, then pending_purchase
            target_item = None
            search_term = None
            quantity = 1  # Default quantity
            
            # For confirm_purchase, try to use pending_purchase from conversation memory
            if is_confirmation and conversation_memory.get('pending_purchase'):
                pending = conversation_memory['pending_purchase']
                pending_item_id = pending.get('item_id')
                print(f"[SHOP] Using pending_purchase: {pending}")
                
                # Find the item by ID from pending purchase
                if pending_item_id:
                    for item in shop_items:
                        item_id = item.get('id') or item.get('name', '').lower().replace(' ', '_')
                        if item_id == pending_item_id:
                            target_item = item
                            print(f"[SHOP] Found item from pending_purchase: {item.get('name')}")
                            break
            
            # If not found from pending, try entities
            if not target_item and entities:
                entity = entities[0]
                search_term = entity.get('id', '') if isinstance(entity, dict) else str(entity)
                # Extract quantity from entity if available
                if isinstance(entity, dict) and 'quantity' in entity:
                    quantity = entity['quantity']
                    print(f"[SHOP] Found quantity in entity: {quantity}")
            # Fall back to subject if entities is empty
            elif not target_item and layer1 and layer1.get('subject'):
                search_term = layer1.get('subject')
            
            # DEBUG: Log what we're searching for
            print(f"[SHOP] Searching for item: search_term='{search_term}', entities={entities}, subject={layer1.get('subject') if layer1 else 'N/A'}")
            print(f"[SHOP] Available items: {[item.get('name', '') for item in shop_items]}")
            
            if not target_item and search_term:
                search_term = search_term.lower()
                for item in shop_items:
                    item_name = item.get('name', item.get('item_name', '')).lower()
                    print(f"[SHOP] Comparing '{search_term}' with '{item_name}'")
                    if search_term in item_name or item_name in search_term:
                        target_item = item
                        print(f"[SHOP] MATCHED: {item.get('name')}")
                        break
            
            if not target_item:
                print(f"[SHOP] NO MATCH FOUND for '{search_term}'")
                
                # If this is a confirmation but we can't find the item, 
                # it might have already been purchased - return success
                if is_confirmation:
                    print(f"[SHOP] Confirmation without item found - assuming purchase already completed")
                    return {
                        "action": "shop_purchase_success",
                        "item_name": "item",
                        "item_price": 0,
                        "npc_emotion": "pleased"
                    }
                
                return {
                    "action": "shop_item_not_found",
                    "requested_item": search_term or 'item',
                    "npc_emotion": "apologetic"
                }
            
            item_price = target_item.get('price', 0)
            player_coins = player_state.get('coins', 0)
            
            # Generate item_id from name if not present in item data
            item_id = target_item.get('id') or target_item.get('name', 'Unknown').lower().replace(' ', '_')
            print(f"[SHOP] Using item_id: {item_id}")
            
            # Check if player has enough money
            total_price = item_price * quantity
            if player_coins >= total_price:
                # Purchase successful - execute it immediately
                return {
                    "action": "shop_purchase_success",
                    "item_id": item_id,
                    "item_name": target_item.get('name', target_item.get('item_name', 'Unknown')),
                    "item_price": item_price,
                    "quantity": quantity,
                    "total_price": total_price,
                    "npc_emotion": "pleased",
                    "world_actions": [
                        {
                            "type": "complete_purchase",
                            "item_id": item_id,
                            "price": total_price,
                            "quantity": quantity
                        }
                    ]
                }
            else:
                # Not enough money
                return {
                    "action": "shop_insufficient_funds",
                    "item_name": target_item.get('name', target_item.get('item_name', 'Unknown')),
                    "item_price": item_price,
                    "npc_emotion": "apologetic"
                }
        
        elif primary_intent == 'sell_item':
            # NPC doesn't buy items
            return {
                "action": "shop_no_buy",
                "npc_emotion": "apologetic"
            }
        
        else:
            # Default to browse
            return self._handle_commerce(npc_data, player_state, 'browse_shop', entities, conversation_memory)
    
    def _handle_training(self, npc_data: Dict, player_state: Dict,
                        primary_intent: str) -> Dict:
        """Handle Training category intents."""
        world_data = npc_data.get('world', {})
        available_quests = world_data.get('available_quests', [])

        # Filter to only technique-learning quests
        techniques = []
        for quest in available_quests:
            rewards = quest.get('rewards', {})
            if rewards.get('technique'):
                techniques.append({
                    "name": quest.get('name', 'Unknown'),
                    "technique": rewards.get('technique'),
                    "description": quest.get('description', '')
                })

        # Also get NPC's known techniques
        npc_techniques = npc_data.get('techniques', [])

        packet = {
            "action": "training_available",
            "npc_emotion": "helpful",
            "teachable_techniques": techniques,
            "npc_techniques": npc_techniques,
            "teaching_style": world_data.get('teaching_style', ''),
            "specialty": world_data.get('specialty', '')
        }

        if techniques:
            packet["message"] = f"I can teach you {len(techniques)} technique(s)"
        elif npc_techniques:
            packet["message"] = f"I know {len(npc_techniques)} technique(s) but require quests to teach them"
        else:
            packet["message"] = "I have nothing to teach at this time"

        return packet
    
    def _handle_services(self, npc_data: Dict, player_state: Dict, 
                        primary_intent: str, entities: List[Dict]) -> Dict:
        """Handle Services category intents."""
        if primary_intent == 'repair_request':
            if entities:
                entity = entities[0]
                item_name = entity.get('id', 'item') if isinstance(entity, dict) else str(entity)
                return {
                    "action": "repair_possible",
                    "item_name": item_name,
                    "npc_emotion": "helpful"
                }
            return {
                "action": "repair_inquiry",
                "npc_emotion": "helpful"
            }
        
        elif primary_intent == 'heal_request':
            return {
                "action": "heal_available",
                "npc_emotion": "helpful"
            }
        
        elif primary_intent == 'buff_request':
            return {
                "action": "buff_available",
                "npc_emotion": "helpful"
            }
        
        else:
            return {
                "action": "service_available",
                "npc_emotion": "helpful"
            }


# Global instance
world_simulator = WorldSimulator()


def simulate_world(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to simulate world state.
    
    Args:
        input_data: Input structure with player_message, npc_data, etc.
    
    Returns:
        Simulation result packet
    """
    return world_simulator.simulate(input_data)