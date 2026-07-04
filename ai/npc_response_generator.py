"""
Layer 3: Response Generator (Narrator Only)

Layer 3 ONLY narrates packet data from Layer 2.
Layer 3 NEVER:
- Accesses game databases
- Invents facts, quests, items, or knowledge
- Makes assumptions about game state
- Decides what information exists

Layer 3 is a NARRATOR, not a content generator.
"""

from typing import Dict, Any, List, Optional
import os
import random
import httpx


class NPCResponseGenerator:
    """Narrates simulation packets into natural dialogue."""
    
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        self.api_token = os.getenv("LM_STUDIO_API_TOKEN", "")
        self.use_llm = True  # Always try Ollama
        
    async def generate_greeting(self, npc: Dict[str, Any], player_id: str) -> str:
        """
        Generate NPC greeting when player initiates conversation.
        
        NOTE: This is a special case - no packet yet, so we use NPC data.
        This should be the ONLY place Layer 3 accesses NPC data directly.
        """
        npc_name = npc.get('name', 'NPC')
        npc_job = npc.get('job', 'villager')
        
        prompt = f"""You are {npc_name}, a {npc_job} in a medieval fantasy world.

Generate a short greeting (max 200 characters) that:
1. Sounds natural for a {npc_job}
2. Is appropriate for a customer/passerby approaching you
3. Starts with a brief action description, then dialogue in quotes

Example format:
"The blacksmith looks up from his anvil. 'Need something forged or repaired?'"

/nothink

Return ONLY the greeting text. No JSON, no explanation.
"""
        
        # LLM ONLY - no fallbacks
        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.ollama_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "system", "content": prompt}],
                    "stream": False
                },
                headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            response = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            
            if not response:
                raise ValueError("Layer 3 returned empty response")
            
            return response
    
    async def generate_response(
        self, 
        npc: Dict[str, Any], 
        player_message: str, 
        intent: str, 
        packet: Dict[str, Any],
        conversation_history: List[Dict[str, str]] = None,
        reasoning_context: Dict[str, Any] = None
    ) -> str:
        """
        Generate NPC response by narrating packet data with full context.
        
        Args:
            npc: NPC basic info (name, job, personality) - ONLY for character voice
            player_message: What the player said
            intent: Detected intent from Layer 1
            packet: Simulation packet from Layer 2 (THE ONLY SOURCE OF TRUTH)
            conversation_history: Full conversation history
            reasoning_context: World reasoning from Layer 2 (conversation_state, world_state, facts, etc.)
        
        Returns:
            Natural language response narrating the packet
        """
        npc_name = packet.get('npc_name', npc.get('name', 'NPC'))
        npc_job = packet.get('npc_job', npc.get('job', 'villager'))
        npc_personality = npc.get('conversation', {}).get('personality', 'friendly')
        action = packet.get('action', 'general_chat')
        
        # Get emotion from reasoning context if available, otherwise from packet
        emotion = packet.get('emotion', 'neutral')
        if reasoning_context:
            emotion = reasoning_context.get('emotion', emotion)
        
        # Build conversation history context
        history_text = ""
        if conversation_history and len(conversation_history) > 0:
            recent_history = conversation_history[-5:]  # Last 5 exchanges for better context
            history_text = "\nRecent conversation:\n"
            for exchange in recent_history:
                speaker = exchange.get('speaker', 'unknown')
                text = exchange.get('text', '')
                if speaker == 'player':
                    history_text += f"Player: {text}\n"
                else:
                    history_text += f"You: {text}\n"
        
        # Build packet data section - THIS IS THE ONLY DATA LAYER 3 USES
        packet_data = self._build_packet_data_section(packet)
        
        # Build reasoning context section
        reasoning_text = ""
        if reasoning_context:
            conv_state = reasoning_context.get('conversation_state', {})
            npc_reasoning = reasoning_context.get('npc_reasoning', {})
            facts = reasoning_context.get('facts_to_share', [])
            world_actions = reasoning_context.get('world_actions', [])
            
            reasoning_text = "\n=== CONVERSATION CONTEXT ===\n"
            reasoning_text += f"Topic: {conv_state.get('topic', 'general')}\n"
            reasoning_text += f"Mode: {conv_state.get('mode', 'general')}\n"
            reasoning_text += f"Stage: {conv_state.get('stage', 'general')}\n"
            reasoning_text += f"\nNPC Thought: {npc_reasoning.get('thought', '')}\n"
            reasoning_text += f"NPC Goal: {npc_reasoning.get('goal', '')}\n"
            reasoning_text += f"\nFacts to Share:\n"
            for fact in facts:
                reasoning_text += f"  - {fact}\n"
            if world_actions:
                reasoning_text += f"\nWorld Actions:\n"
                for action in world_actions:
                    reasoning_text += f"  - {action.get('type', 'unknown')}\n"
        
        # Build the narration prompt
        prompt = f"""/no_think

You are {npc_name}, a {npc_job} in a medieval fantasy world.

Your emotional tone: {emotion}

{history_text}

Player just said: "{player_message}"

Player intent: {intent}

{reasoning_text}

Simulation packet:
{packet_data}
Narrate the simulation naturally.

RULES:
1. ONLY narrate what is in the packet and context above
2. NEVER add information not provided
3. NEVER invent facts, quest details, item descriptions, or knowledge
4. If there are facts to share, share ONLY those facts
5. If there are world actions, narrate ONLY those actions
6. Keep responses under 300 characters
7. Stay in character as {npc_name} the {npc_job}
8. When narrating physical action USE third person, when narrating dialogue use quotes
9. DO NOT include the quest name, only explain what is required to complete the quest in the dialogue
10. DO NOT include the action name in your response - only the action description and dialogue

Write exactly one natural response.

If an action description exists,
begin with a short physical action in third person.

Then write the NPC's dialogue.

Do not output labels, placeholders or templates.

No brackets.

No "Dialogue".

No "Action description".

EXAMPLES:
- "The blacksmith looks up from his anvil. 'Need something forged or repaired?'"
- "The guard nods. 'I've heard rumors of goblins in the eastern forest. Stay safe.'"
- "The merchant gestures to his wares. 'I've got iron swords for 50 gold each.'"

BAD EXAMPLES (do NOT do this):
- "shop_purchase_success". "You've purchased..." (WRONG - includes action name)
- "The blacksmith says. 'Hello.'" (WRONG - "says" is not an action description)

DO NOT INVENT ANY INFORMATION. ONLY NARRATE WHAT IS IN THE PACKET AND CONTEXT ABOVE.


Return ONLY the response text. No JSON, no explanation.
"""
        
        # DEBUG: Log the prompt
        print("\n" + "="*80)
        print("LAYER 3 PROMPT (sent to LLM)")
        print("="*80)
        print(prompt)
        print("="*80 + "\n")
        
        try:
            headers = {}
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"
            
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.ollama_url}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [{"role": "system", "content": prompt}],
                        "stream": False
                    },
                    headers=headers
                )
                resp.raise_for_status()
                data = resp.json()
                response = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                
                if not response:
                    raise ValueError("Layer 3 returned empty response")
                
                return response
            
        except Exception as e:
            # Layer 3 failed - stop processing
            raise RuntimeError(f"Layer 3 (Response Generation) failed: {str(e)}")
    
    def _build_packet_data_section(self, packet: Dict[str, Any]) -> str:
        """Build the packet data section for the prompt - THE ONLY DATA LAYER 3 USES."""
        action = packet.get('action', 'general_chat')
        data_section = f"Action: {action}\n"
        
        # Shop actions
        if action == 'shop_browse':
            # Use categorized items if available
            if packet.get('shop_categories'):
                categories = packet['shop_categories']
                data_section += "Shop inventory:\n"
                for category, items in categories.items():
                    if items:
                        data_section += f"\n{category.title()}:\n"
                        for item in items:
                            data_section += f"  - {item.get('name', 'Unknown')}: {item.get('price', 0)} gold\n"
            else:
                # Fallback to old format
                items = packet.get('visible_items', [])
                data_section += f"Items for sale:\n"
                for item in items:
                    data_section += f"  - {item.get('name', 'Unknown')}: {item.get('price', 0)} gold\n"
        
        elif action == 'shop_offer_purchase':
            data_section += f"Item: {packet.get('item_name', 'Unknown')}\n"
            data_section += f"Price: {packet.get('item_price', 0)} gold\n"
            data_section += "Status: Offering for sale (not yet purchased)\n"
        
        elif action == 'shop_purchase_success':
            data_section += f"Item: {packet.get('item_name', 'Unknown')}\n"
            data_section += f"Price: {packet.get('item_price', 0)} gold\n"
            data_section += "Status: PURCHASE COMPLETE\n"
        
        elif action == 'shop_item_not_found':
            data_section += f"Requested: {packet.get('requested_item', 'item')}\n"
            data_section += "Message: NPC doesn't sell that\n"
        
        elif action == 'shop_insufficient_funds':
            data_section += f"Item: {packet.get('item_name', 'Unknown')}\n"
            data_section += f"Price: {packet.get('item_price', 0)} gold\n"
            data_section += "Message: Player can't afford\n"
        
        elif action == 'shop_no_buy':
            data_section += "Message: NPC doesn't buy items\n"
        
        elif action == 'shop_empty':
            data_section += "Message: No items for sale\n"
        
        # Quest actions
        elif action == 'offer_quest':
            data_section += f"Quest: {packet.get('quest_title', 'Unknown')}\n"
            data_section += f"Description: {packet.get('quest_description', '')}\n"
            rewards = packet.get('rewards', {})
            if rewards:
                data_section += f"Rewards: {rewards.get('gold', 0)} gold"
                if rewards.get('items'):
                    data_section += f", {len(rewards['items'])} items"
                data_section += "\n"
        
        elif action == 'quest_list_available':
            quests = packet.get('available_quests', [])
            data_section += f"Available quests:\n"
            for quest in quests:
                data_section += f"  - {quest.get('quest_title', 'Unknown')}: {quest.get('quest_summary', '')}\n"
        
        elif action == 'no_quests_available':
            data_section += "Message: No quests available\n"
        
        # Service actions
        elif action == 'craft_possible':
            data_section += f"Can craft: {packet.get('item_name', 'item')}\n"
        
        elif action == 'craft_inquiry':
            data_section += "Message: What would you like crafted?\n"
        
        elif action == 'repair_possible':
            data_section += f"Can repair: {packet.get('item_name', 'item')}\n"
        
        elif action == 'repair_inquiry':
            data_section += "Message: What needs repairing?\n"
        
        elif action == 'training_available':
            data_section += f"Message: {packet.get('message', 'Training is available')}\n"
            teachable = packet.get('teachable_techniques', [])
            if teachable:
                data_section += "Teachable techniques:\n"
                for t in teachable:
                    data_section += f"  - {t.get('name')}: {t.get('technique')}\n"
            npc_techs = packet.get('npc_techniques', [])
            if npc_techs:
                data_section += f"NPC knows: {', '.join(npc_techs)}\n"
            if packet.get('teaching_style'):
                data_section += f"Teaching style: {packet.get('teaching_style')}\n"
            if packet.get('specialty'):
                data_section += f"Specialty: {packet.get('specialty')}\n"

        
        # Information actions
        elif action == 'share_information':
            data_section += f"Topic: {packet.get('topic', '')}\n"
            data_section += "Message: Share knowledge about this topic\n"
        
        elif action == 'knowledge_no_info':
            data_section += "Message: Don't know about that\n"
        
        # Response actions
        elif action == 'confirmation_received':
            data_section += "Message: Player confirmed\n"
        
        elif action == 'denial_received':
            data_section += "Message: Player declined\n"
        
        elif action == 'acknowledgement_received':
            data_section += "Message: Player acknowledged\n"
        
        # Default
        elif action == 'greeting':
            data_section += "Message: Greet the player\n"
        
        elif action == 'farewell':
            data_section += "Message: Say goodbye\n"
        
        elif action == 'general_chat':
            data_section += "Message: General conversation\n"
        
        return data_section
