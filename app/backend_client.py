from typing import Optional, Dict
import httpx
import secrets
import string
from .config import settings
from .logger import logger


class BackendClient:
    def __init__(self):
        self.base_url = settings.backend_url.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
        }

    def _generate_email(self, telegram_user_id: int, telegram_username: Optional[str] = None) -> str:
        """Генерирует email на основе telegram_user_id"""
        if telegram_username:
            # Используем username если есть, очищаем от недопустимых символов
            safe_username = telegram_username.replace("@", "").lower()
            return f"tg_{safe_username}_{telegram_user_id}@telegram.local"
        return f"tg_user_{telegram_user_id}@telegram.local"

    def _generate_password(self, length: int = 16) -> str:
        """Генерирует случайный безопасный пароль"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    async def check_telegram_username(self, telegram_username: str) -> bool:
        """
        Проверяет, существует ли пользователь с данным telegram_username.
        
        Returns:
            True если пользователь существует, False если нет
        """
        url = f"{self.base_url}/api/auth/check-telegram-username"
        params = {"telegram_username": telegram_username}
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self.headers, params=params)
                r.raise_for_status()
                data = r.json()
                # Предполагаем, что ответ содержит поле exists или similar
                return data.get("exists", False) or data.get("user_exists", False)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            logger.error("Backend API error: %s - %s", e.response.status_code, e.response.text)
            return False
        except Exception as e:
            logger.exception("Backend API call failed: %s", e)
            return False

    async def register(
        self,
        email: str,
        password: str,
        business_type: str = "other",
        telegram_username: Optional[str] = None,
        full_name: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Регистрирует нового пользователя.
        
        Returns:
            Словарь с токеном и данными пользователя или None в случае ошибки
        """
        url = f"{self.base_url}/api/auth/register"
        payload = {
            "email": email,
            "password": password,
            "business_type": business_type,
        }
        if telegram_username:
            payload["telegram_username"] = telegram_username
        if full_name:
            payload["full_name"] = full_name

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(url, headers=self.headers, json=payload)
                r.raise_for_status()
                data = r.json()
                return {
                    "token": data.get("token"),
                    "user_id": data.get("user_id"),
                    "email": email,
                    "password": password,  # Сохраняем для будущих логинов
                }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400 or e.response.status_code == 409:
                # Пользователь уже существует
                raise Exception(f"User already exists: {e.response.text}")
            logger.error("Backend API error: %s - %s", e.response.status_code, e.response.text)
            return None
        except Exception as e:
            logger.exception("Backend API call failed: %s", e)
            return None

    async def login(self, email: str, password: str) -> Optional[Dict]:
        """
        Логинит пользователя.
        
        Returns:
            Словарь с токеном или None в случае ошибки
        """
        url = f"{self.base_url}/api/auth/login"
        payload = {
            "email": email,
            "password": password,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(url, headers=self.headers, json=payload)
                r.raise_for_status()
                data = r.json()
                return {
                    "token": data.get("token"),
                    "user_id": data.get("user_id"),
                }
        except httpx.HTTPStatusError as e:
            logger.error("Backend API error: %s - %s", e.response.status_code, e.response.text)
            return None
        except Exception as e:
            logger.exception("Backend API call failed: %s", e)
            return None

    async def get_profile(self, token: str) -> Optional[Dict]:
        """
        Получает профиль пользователя по токену.
        """
        url = f"{self.base_url}/api/auth/profile"
        params = {"token": token}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self.headers, params=params)
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            logger.error("Backend API error: %s - %s", e.response.status_code, e.response.text)
            return None
        except Exception as e:
            logger.exception("Backend API call failed: %s", e)
            return None

    async def create_or_get_telegram_user(
        self,
        telegram_user_id: int,
        telegram_username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Создает или получает существующего Telegram пользователя.
        
        Returns:
            Словарь с данными Telegram пользователя или None в случае ошибки
        """
        url = f"{self.base_url}/api/telegram/users"
        payload = {
            "telegram_user_id": telegram_user_id,
        }
        if telegram_username:
            payload["telegram_username"] = telegram_username
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(url, headers=self.headers, json=payload)
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            logger.error("Backend API error: %s - %s", e.response.status_code, e.response.text)
            return None
        except Exception as e:
            logger.exception("Backend API call failed: %s", e)
            return None

    async def get_telegram_user(self, telegram_user_id: int) -> Optional[Dict]:
        """
        Получает Telegram пользователя по его ID.
        
        Returns:
            Словарь с данными Telegram пользователя или None в случае ошибки
        """
        url = f"{self.base_url}/api/telegram/users/{telegram_user_id}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self.headers)
                r.raise_for_status()
                data = r.json()
                logger.info("Telegram user API response for user_id %s: %s", telegram_user_id, data)
                return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.info("Telegram user %s not found (404)", telegram_user_id)
                return None
            logger.error("Backend API error: %s - %s", e.response.status_code, e.response.text)
            return None
        except Exception as e:
            logger.exception("Backend API call failed: %s", e)
            return None

    async def link_telegram_user(self, telegram_user_id: int, backend_user_id: int) -> Optional[Dict]:
        """
        Связывает Telegram пользователя с основным аккаунтом.
        
        Returns:
            Результат связывания или None в случае ошибки
        """
        url = f"{self.base_url}/api/telegram/users/{telegram_user_id}/link"
        payload = {
            "user_id": backend_user_id,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(url, headers=self.headers, json=payload)
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            logger.error("Backend API error: %s - %s", e.response.status_code, e.response.text)
            return None
        except Exception as e:
            logger.exception("Backend API call failed: %s", e)
            return None

    async def send_message(self, user_id: int, message: str) -> Optional[str]:
        """
        Отправляет сообщение на backend API и возвращает ответ.
        
        Args:
            user_id: ID пользователя (backend user_id)
            message: Текст сообщения пользователя
            
        Returns:
            Ответ от AI или None в случае ошибки
        """
        url = f"{self.base_url}/api/chat/message"
        payload = {
            "user_id": str(user_id),  # Backend ожидает строку
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

