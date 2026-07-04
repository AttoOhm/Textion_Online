from typing import Dict, Any, Optional, List
import os
import httpx

class NarrationGenerator:
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        self.use_llm = True  # Always try Ollama
        
    async def generate_narration(self, events: List[Dict[str, Any]], player_context: Dict[str, Any]) -> str:
        """Generate elegant narration from world events"""
        if not events:
            return ""
        
        # Format events for the prompt
        events_text = "\n".join([self.format_event(event) for event in events])
        
        # Get player context
        player_location = player_context.get('location', 'unknown')
        player_name = player_context.get('name', 'Player')
        
        prompt = f"""You are a skilled narrator for a medieval fantasy text-based RPG.

Player: {player_name}
Current location: {player_location}

Events that occurred during this time tick:
{events_text}

Generate an elegant, immersive narration (max 500 characters) that:
1. Describes what happened in a natural, flowing manner
2. Uses atmospheric language appropriate for the setting
3. Combines related events where possible
4. Focuses on what the player would perceive

Format: Write as third-person narration. Use present tense.
Example: "The forest grows quiet as the wolf retreats into the shadows. Nearby, a merchant adjusts his wares, eyeing you with mild curiosity."
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
            # Fallback to simple event listing
            return self.simple_narration(events)
    
    def format_event(self, event: Dict[str, Any]) -> str:
        """Format a single event for the prompt"""
        event_type = event.get('type', 'unknown')
        
        if event_type == 'combat':
            return f"- Combat: {event.get('description', 'A fight occurred.')}"
        elif event_type == 'movement':
            return f"- Movement: {event.get('description', 'Something moved.')}"
        elif event_type == 'interaction':
            return f"- Interaction: {event.get('description', 'Something happened.')}"
        elif event_type == 'action':
            return f"- Action: {event.get('description', 'An action was taken.')}"
        else:
            return f"- Event: {event.get('description', 'An event occurred.')}"
    
    def simple_narration(self, events: List[Dict[str, Any]]) -> str:
        """Simple fallback narration without LLM"""
        if not events:
            return ""
        
        descriptions = [event.get('description', '') for event in events if event.get('description')]
        
        if len(descriptions) == 1:
            return descriptions[0]
        elif len(descriptions) > 1:
            return " ".join(descriptions)
        else:
            return "The world continues its quiet rhythm."
    
    async def generate_combat_narration(self, combat_events: List[Dict[str, Any]], player_context: Dict[str, Any]) -> str:
        """Generate specialized combat narration"""
        if not combat_events:
            return ""
        
        # Build combat summary
        combat_summary = []
        for event in combat_events:
            if event.get('type') == 'combat':
                attacker = event.get('attacker', 'Unknown')
                target = event.get('target', 'Unknown')
                damage = event.get('damage', 0)
                combat_summary.append(f"{attacker} hits {target} for {damage} damage")
        
        summary_text = "; ".join(combat_summary)
        
        prompt = f"""You are a combat narrator for a medieval fantasy text-based RPG.

Player: {player_context.get('name', 'Player')}
Location: {player_context.get('location', 'battlefield')}

Combat actions: {summary_text}

Generate an exciting combat narration (max 300 characters) that:
1. Captures the intensity of battle
2. Uses dynamic, action-oriented language
3. Describes the flow of combat

Example: "Steel clashes as you swing your blade, finding its mark. The enemy staggers back, wounded but still standing."
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            # Fallback
            return f"Combat ensues! {summary_text}"