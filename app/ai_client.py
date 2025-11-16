from typing import List, Dict, Any
import httpx
from .config import settings

class AIClient:
    def __init__(self):
        self.base_url = settings.ai_base_url.rstrip("/")
        self.model = settings.ai_model
        self.provider = settings.ai_provider.lower()
        self.headers = {
            "Authorization": f"Bearer {settings.ai_api_key}",
            "Content-Type": "application/json",
        }
        if self.provider == "openrouter":
            # Optional headers OpenRouter recommends
            self.headers.setdefault("HTTP-Referer", "https://github.com/")
            self.headers.setdefault("X-Title", "Telegram AI Bot")

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=self.headers, json=payload)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
