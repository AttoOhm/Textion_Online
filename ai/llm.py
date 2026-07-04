"""
LLM integration - talks to Ollama for NPC conversations and narration.
"""
import os
import httpx
import json


class LLM:
    def __init__(self):
        self.url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "60"))
    
    async def complete(self, user_prompt: str, system_prompt: str = None) -> str | None:
        """Send a prompt to Ollama and return the response text."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.url}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            print(f"[LLM Error] {e}")
            return None
    
    async def complete_json(self, user_prompt: str, system_prompt: str = None) -> dict | None:
        """Send a prompt and parse the response as JSON."""
        raw = await self.complete(user_prompt, system_prompt)
        if not raw:
            return None
        try:
            t = raw.strip()
            if t.startswith("```"):
                t = t.replace("```json\n", "").replace("```\n", "").replace("```", "")
            start = t.find("{")
            end = t.rfind("}")
            if start != -1 and end != -1:
                t = t[start:end+1]
            return json.loads(t)
        except Exception:
            return None


llm = LLM()