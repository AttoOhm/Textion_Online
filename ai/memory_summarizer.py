from typing import Dict, Any, Optional, List
import os
import httpx

class MemorySummarizer:
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        self.use_llm = True  # Always try Ollama
        
    async def summarize_event(self, event: Dict[str, Any], importance_threshold: int = 30) -> Optional[Dict[str, Any]]:
        """Summarize an event and determine if it's worth remembering"""
        event_type = event.get('type', 'unknown')
        importance = self.calculate_importance(event)
        
        # Only remember events above threshold
        if importance < importance_threshold:
            return None
        
        # Generate summary
        summary = await self.generate_summary(event)
        
        return {
            'type': event_type,
            'importance': importance,
            'summary': summary,
            'timestamp': event.get('timestamp', 0),
            'details': {
                'location': event.get('location'),
                'entities_involved': event.get('entities_involved', []),
                'key_outcome': event.get('key_outcome')
            }
        }
    
    def calculate_importance(self, event: Dict[str, Any]) -> int:
        """Calculate event importance (0-100)"""
        event_type = event.get('type', 'unknown')
        
        # Base importance by event type
        base_importance = {
            'quest_complete': 95,
            'quest_start': 90,
            'boss_defeat': 85,
            'combat': 70,
            'item_acquired': 60,
            'level_up': 65,
            'death': 80,
            'exploration': 40,
            'conversation': 30,
            'movement': 10,
            'ambient': 5
        }
        
        base = base_importance.get(event_type, 30)
        
        # Modify based on context
        modifier = 0
        
        # Important entities increase importance
        important_entities = ['boss', 'quest_giver', 'merchant', 'guard_captain']
        entities = event.get('entities_involved', [])
        if any(entity in important_entities for entity in entities):
            modifier += 15
        
        # Location importance
        important_locations = ['throne_room', 'dungeon_boss', 'ancient_ruins']
        if event.get('location') in important_locations:
            modifier += 10
        
        # Player involvement increases importance
        if event.get('player_involved', False):
            modifier += 20
        
        return min(100, base + modifier)
    
    async def generate_summary(self, event: Dict[str, Any]) -> str:
        """Generate a concise summary of an event"""
        
        prompt = f"""Generate a concise summary (max 50 words) of this game event for a player's memory log.

Event type: {event.get('type', 'unknown')}
Description: {event.get('description', 'No description available')}
Location: {event.get('location', 'unknown')}
Outcome: {event.get('key_outcome', 'none')}

Requirements:
1. Be concise and clear
2. Focus on key facts the player would remember
3. Use past tense
4. Maximum 50 words

Example: "Defeated the goblin chief in the dark forest cave, acquiring the ancient amulet."
"""
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.ollama_url}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [{"role": "system", "content": prompt}],
                        "stream": False
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            
        except Exception as e:
            # Fallback to simple summary
            return self.simple_summary(event)
    
    def simple_summary(self, event: Dict[str, Any]) -> str:
        """Simple summary without LLM"""
        event_type = event.get('type', 'event')
        description = event.get('description', 'Something happened')
        
        return f"[{event_type.upper()}] {description}"
    
    async def condense_memories(self, memories: List[Dict[str, Any]], max_memories: int = 100) -> List[Dict[str, Any]]:
        """Condense memory list when it gets too long"""
        if len(memories) <= max_memories:
            return memories
        
        # Sort by importance
        sorted_memories = sorted(memories, key=lambda x: x.get('importance', 0), reverse=True)
        
        # Keep most important memories
        kept_memories = sorted_memories[:max_memories]
        
        # Archive older, less important memories
        archived = sorted_memories[max_memories:]
        
        if archived:
            # Create a summary of archived memories
            archive_summary = await self.generate_archive_summary(archived)
            kept_memories.append({
                'type': 'archive',
                'importance': 50,
                'summary': archive_summary,
                'timestamp': 0,
                'details': {
                    'archived_count': len(archived),
                    'types': list(set(m.get('type') for m in archived))
                }
            })
        
        return kept_memories
    
    async def generate_archive_summary(self, memories: List[Dict[str, Any]]) -> str:
        """Generate summary for archived memories"""
        if not memories:
            return ""
        
        memory_summaries = [m.get('summary', '') for m in memories[:10]]  # Take first 10
        
        prompt = f"""Summarize these game events into a brief paragraph (max 100 words):

{chr(10).join(memory_summaries)}

Requirements:
1. Combine related events
2. Focus on major themes and outcomes
3. Maximum 100 words
"""
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.ollama_url}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [{"role": "system", "content": prompt}],
                        "stream": False
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            
        except Exception as e:
            return f"Previously: {len(memories)} events occurred."
