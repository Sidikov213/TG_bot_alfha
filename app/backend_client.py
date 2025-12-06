from typing import Optional
import httpx
from .config import settings
from .logger import logger


class BackendClient:
    def __init__(self):
        self.base_url = settings.backend_url.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
        }

    async def send_message(self, user_id: int, message: str) -> Optional[str]:
        """
        Отправляет сообщение на backend API и возвращает ответ.
        
        Args:
            user_id: ID пользователя Telegram (будет использован как user_id для backend)
            message: Текст сообщения пользователя
            
        Returns:
            Ответ от AI или None в случае ошибки
        """
        url = f"{self.base_url}/api/chat/message"
        payload = {
            "user_id": user_id,
            "message": message,
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(url, headers=self.headers, json=payload)
                r.raise_for_status()
                data = r.json()
                # Пробуем разные варианты формата ответа
                # Если ответ - строка напрямую, возвращаем её
                if isinstance(data, str):
                    return data
                # Иначе ищем в полях response, message, text, content
                return (
                    data.get("response") 
                    or data.get("message") 
                    or data.get("text") 
                    or data.get("content")
                    or (data.get("data", {}).get("response") if isinstance(data.get("data"), dict) else None)
                )
        except httpx.HTTPStatusError as e:
            logger.error("Backend API error: %s - %s", e.response.status_code, e.response.text)
            return None
        except Exception as e:
            logger.exception("Backend API call failed: %s", e)
            return None

