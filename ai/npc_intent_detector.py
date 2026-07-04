"""
Layer 1: Understanding Engine

SINGLE RESPONSIBILITY: Understand which game system the player is trying to interact with.

Layer 1 receives:
- Player message
- Full conversation history (from NPC greeting)
- NPC capabilities

Layer 1 outputs:
- Category (which game system)
- Primary intent (what they want to do)
- Secondary intent (additional context)
- Subject (specific thing being discussed)
- Entities (things mentioned)
- Attitude, emotion, seriousness

Layer 1 does NOT:
- Simulate world state
- Decide outcomes
- Generate NPC reasoning
- Access game data
"""

from typing import Dict, Any, List, Optional
import re
import os
import json
import asyncio
import httpx


class Layer1Interpreter:
    """Understanding engine based on NPC capabilities."""
    
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        self.api_token = os.getenv("LM_STUDIO_API_TOKEN", "")
    
    async def understand(self,
                        player_message: str,
                        full_conversation: List[Dict[str, str]] = None,
                        npc_capabilities: Dict[str, Any] = None,
                        npc_knowledge_topics: List[str] = None,
                        npc_quest_ids: List[str] = None,
                        npc_quest_names: List[str] = None,
                        npc_shop_items: List[str] = None) -> Dict[str, Any]:
        """
        Understand player message in context of NPC capabilities.
        
        Args:
            player_message: What the player said
            full_conversation: Complete conversation from NPC greeting
            npc_capabilities: NPC's capability definitions
            npc_knowledge_topics: List of topics NPC knows about
            npc_quest_ids: List of quest IDs NPC can offer
            npc_quest_names: List of quest names NPC can offer
            npc_shop_items: List of item names NPC sells
        
        Returns:
            {
                "category": "Commerce",
                "primary_intent": "browse_shop",
                "secondary_intent": "shop_information",
                "subject": "iron sword",
                "entities": [...],
                "attitude": "...",
                "emotion": "...",
                "seriousness": 0.5
            }
        
        Raises:
            RuntimeError: If LLM fails or returns invalid JSON
        """
        if full_conversation is None:
            full_conversation = []
        if npc_capabilities is None:
            npc_capabilities = {}
        if npc_knowledge_topics is None:
            npc_knowledge_topics = []
        if npc_quest_ids is None:
            npc_quest_ids = []
        if npc_quest_names is None:
            npc_quest_names = []
        if npc_shop_items is None:
            npc_shop_items = []
        
        # LLM ONLY - no fallbacks, no defaults
        result = await self._llm_understand(
            player_message, full_conversation, npc_capabilities,
            npc_knowledge_topics, npc_quest_ids, npc_quest_names, npc_shop_items
        )
        
        # Validate output - fill in missing fields with defaults instead of failing
        validation_result = self._validate_output(result)
        if not validation_result:
            # Fill in missing fields with sensible defaults
            defaults = {
                'category': result.get('category', 'General'),
                'primary_intent': result.get('primary_intent', 'general_chat'),
                'secondary_intent': result.get('secondary_intent', 'conversation'),
                'subject': result.get('subject'),
                'entities': result.get('entities', []),
                'attitude': result.get('attitude', 'neutral'),
                'emotion': result.get('emotion', 'neutral'),
                'seriousness': result.get('seriousness', 0.5)
            }
            result = defaults
            print(f"[LAYER1] Filled missing fields with defaults: {json.dumps(result, indent=2)}")
        
        return result
    
    def _validate_output(self, result: Dict) -> bool:
        """Validate output format - check structure only, not content quality."""
        required = ['category', 'primary_intent', 'secondary_intent', 
                    'subject', 'entities', 'attitude', 'emotion', 'seriousness']
        
        # Check all required fields exist
        if not all(field in result for field in required):
            return False
        
        # Check types - allow null/empty for subject, pass through exactly what LLM returns
        for field in ['category', 'primary_intent', 'secondary_intent', 'attitude', 'emotion']:
            if not isinstance(result[field], str):
                return False
        
        # Subject can be string or null
        if not (isinstance(result['subject'], str) or result['subject'] is None):
            return False
        
        # Check entities is a list
        if not isinstance(result['entities'], list):
            return False
        
        # Check seriousness is a number
        if not isinstance(result['seriousness'], (int, float)):
            return False
        
        return True
    
    def _build_prompt(self, player_message: str, full_conversation: List[Dict], 
                      npc_capabilities: Dict,
                      npc_knowledge_topics: List[str] = None,
                      npc_quest_ids: List[str] = None,
                      npc_quest_names: List[str] = None,
                      npc_shop_items: List[str] = None) -> str:
        """Build Layer 1 understanding prompt."""
        
        # Build conversation context
        conversation_text = ""
        if full_conversation:
            lines = []
            for exchange in full_conversation:
                speaker = exchange.get('speaker', 'unknown')
                text = exchange.get('text', '')
                lines.append(f"{speaker.upper()}: {text}")
            conversation_text = "\n".join(lines)
        else:
            conversation_text = "No prior conversation."
        
        # Build capabilities text
        capabilities_text = ""
        if npc_capabilities:
            capabilities_text = "\nNPC Capabilities:\n"
            for category, abilities in npc_capabilities.items():
                capabilities_text += f"\n{category}:\n"
                for ability, available in abilities.items():
                    if available:
                        capabilities_text += f"  - {ability}\n"
        
        # Build NPC-specific lists for subject matching
        npc_lists_text = ""
        if npc_knowledge_topics or npc_quest_ids or npc_shop_items:
            npc_lists_text = "\nNPC AVAILABLE TOPICS/ITEMS/QUESTS:\n"
            if npc_knowledge_topics:
                npc_lists_text += f"\nInformation Topics: {', '.join(npc_knowledge_topics)}\n"
            if npc_quest_ids:
                npc_lists_text += f"\nQuest IDs: {', '.join(npc_quest_ids)}\n"
            if npc_quest_names:
                npc_lists_text += f"Quest Names: {', '.join(npc_quest_names)}\n"
            if npc_shop_items:
                npc_lists_text += f"\nShop Items: {', '.join(npc_shop_items[:20])}\n"  # Limit to 20 items
            npc_lists_text += "\nIMPORTANT: Subject MUST match one of the above exactly when possible.\n"
        
        # Build examples section separately to avoid f-string formatting issues
        examples_section = """
EXAMPLES:

Player: "What do you have for sale?"
Category: Commerce
Primary Intent: browse_shop
Secondary Intent: shop_information
Subject: null

Player: "Do you sell swords?"
Category: Commerce
Primary Intent: shop_information
Secondary Intent: browse_shop
Subject: "swords"

Player: "How much is the iron sword?"
Category: Commerce
Primary Intent: ask_price
Secondary Intent: shop_information
Subject: "iron sword"

Player: "I'd like to buy an iron sword."
Category: Commerce
Primary Intent: buy_item
Secondary Intent: shop_information
Subject: "iron sword"

Player: "Yes, I'll take it." (after NPC offered an item)
Category: Commerce
Primary Intent: confirm_purchase
Secondary Intent: shop_information
Subject: null (confirms the pending purchase)

Player: "Tell me about iron swords."
Category: Information
Primary Intent: ask_item
Secondary Intent: ask_npc
Subject: "iron swords"

Player: "Do you know anything about wolves?"
Category: Information
Primary Intent: ask_creature
Secondary Intent: ask_npc
Subject: "wolves"

Player: "Need any help?"
Category: Quest
Primary Intent: quest_interest
Secondary Intent: quest_information
Subject: null

Player: "I'll do it."
Category: Quest
Primary Intent: quest_accept
Secondary Intent: quest_information
Subject: null (accepts whatever was just offered)

Player: "I'm ready to complete the quest"
Category: Quest
Primary Intent: quest_finish
Secondary Intent: quest_completion
Subject: null (completes active quest)

Player: "Can you train me?"
Category: Training
Primary Intent: training_interest
Secondary Intent: learn_technique
Subject: null

OUTPUT

Return ONLY JSON.

{
  "category": "...",
  "primary_intent": "...",
  "secondary_intent": "...",
  "subject": "...",
  "entities": [],
  "attitude": "...",
  "emotion": "...",
  "seriousness": 0.0
}
"""
        
        # Build prompt using string concatenation to avoid f-string brace issues
        prompt_parts = [
            "/no_think\n",
            "\nYou are Layer 1 of a MMORPG NPC interaction system.\n",
            "\nYour ONLY job is to determine WHICH NPC CAPABILITY\nthe player is attempting to use.\n",
            "\nYou are NOT a chatbot.\n",
            "\nYou are NOT the NPC.\n",
            "\nYou do NOT answer the player.\n",
            "\nYou only classify intent.\n",
            "\nNPC CAPABILITIES\n",
            capabilities_text,
            "\nCONVERSATION\n",
            conversation_text,
            "\nLatest Player Message:\n",
            f'\n"{player_message}"\n',
            npc_lists_text,
            "\nRULE\n",
            "\nThe goal is NOT to determine what words mean.\n",
            "\nThe goal is to determine which NPC capability\nthe player is attempting to use.\n",
            "\nAlways prefer a capability interaction over\na generic information request.\n",
            "\nSUBJECT EXTRACTION\n",
            "\nExtract the SUBJECT of the conversation - the specific thing being discussed.\n",
            "\nFor Commerce category:\n- Extract item names: \"iron sword\", \"health potion\", \"shield\"\n- Use exact names from NPC's shop inventory if mentioned\n",
            "\nFor Quest category:\n- Extract quest names or keywords: \"wolf hunting\", \"goblin threat\"\n- Use exact quest names from NPC's available_quests if mentioned\n",
            "\nFor Information category:\n- Extract topic keywords: \"wolves\", \"blacksmithing\", \"village history\"\n- Use keywords from NPC's knowledge section if mentioned\n",
            "\nFor Training category:\n- Extract technique/skill names: \"sword mastery\", \"heavy armor\"\n",
            examples_section
        ]
        
        return ''.join(prompt_parts)
    
    async def _llm_understand(self, player_message: str, full_conversation: List[Dict],
                             npc_capabilities: Dict,
                             npc_knowledge_topics: List[str] = None,
                             npc_quest_ids: List[str] = None,
                             npc_quest_names: List[str] = None,
                             npc_shop_items: List[str] = None) -> Dict[str, Any]:
        """Use LLM for understanding."""
        prompt = self._build_prompt(
            player_message, full_conversation, npc_capabilities,
            npc_knowledge_topics, npc_quest_ids, npc_quest_names, npc_shop_items
        )
        
        # DEBUG: Log the prompt
        print("\n" + "="*80)
        print("LAYER 1 PROMPT (sent to LLM)")
        print("="*80)
        print(prompt)
        print("="*80 + "\n")
        
        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.ollama_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": "Understand this player message."}
                    ],
                    "stream": False
                },
                headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            raw_response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # DEBUG: Log raw LLM response
            print("\n" + "="*80)
            print("LAYER 1 RAW LLM RESPONSE")
            print("="*80)
            print(raw_response)
            print("="*80 + "\n")
            
            # Parse JSON from response
            # Try to find JSON in the response - use simple greedy match
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            
            if json_match:
                try:
                    result = json_match.group()
                    # Clean up common LLM JSON issues
                    result = re.sub(r',\s*\}', '}', result)
                    result = re.sub(r',\s*\]', ']', result)
                    result = re.sub(r'[\r\n\t]', ' ', result)
                    parsed = json.loads(result)
                    
                    # DEBUG: Log parsed JSON
                    print("\n" + "="*80)
                    print("LAYER 1 PARSED JSON")
                    print("="*80)
                    print(json.dumps(parsed, indent=2))
                    print("="*80 + "\n")
                    
                    return parsed
                except json.JSONDecodeError as e:
                    # Show the ACTUAL JSON parsing error
                    print(f"\n{'='*80}")
                    print(f"JSON DECODE ERROR: {e}")
                    print(f"{'='*80}")
                    print(f"Attempted to parse: {json_match.group()}")
                    print(f"{'='*80}\n")
                    raise ValueError(f"JSON parsing failed: {e}\nAttempted to parse: {json_match.group()[:500]}")
                except Exception as e:
                    print(f"\n{'='*80}")
                    print(f"UNEXPECTED ERROR: {type(e).__name__}: {e}")
                    print(f"{'='*80}\n")
                    raise
            else:
                print(f"\n{'='*80}")
                print(f"NO JSON PATTERN FOUND IN RESPONSE")
                print(f"{'='*80}")
                print(f"Raw response: {raw_response}")
                print(f"{'='*80}\n")
        
        raise ValueError(f"No JSON found in LLM response. Raw response: {raw_response[:500]}")


# Global instance
intent_detector = Layer1Interpreter()