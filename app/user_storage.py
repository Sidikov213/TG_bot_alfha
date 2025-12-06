"""
Хранилище для маппинга Telegram пользователей и их данных в backend.
В production лучше использовать базу данных или Redis.
"""
from typing import Optional, Dict
import json
import os
from pathlib import Path


class UserStorage:
    def __init__(self, storage_file: str = "user_storage.json"):
        self.storage_file = Path(storage_file)
        self._storage: Dict[int, Dict] = {}
        self._load()

    def _load(self) -> None:
        """Загружает данные из файла"""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    self._storage = json.load(f)
                    # Конвертируем ключи обратно в int
                    self._storage = {int(k): v for k, v in self._storage.items()}
            except Exception as e:
                print(f"Error loading storage: {e}")
                self._storage = {}

    def _save(self) -> None:
        """Сохраняет данные в файл"""
        try:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(self._storage, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving storage: {e}")

    def get(self, telegram_user_id: int) -> Optional[Dict]:
        """Получает данные пользователя"""
        return self._storage.get(telegram_user_id)

    def set(
        self,
        telegram_user_id: int,
        backend_user_id: Optional[int] = None,
        token: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        telegram_username: Optional[str] = None,
        conversation_id: Optional[int] = None,
    ) -> None:
        """Сохраняет данные пользователя"""
        if telegram_user_id not in self._storage:
            self._storage[telegram_user_id] = {}
        
        if backend_user_id is not None:
            self._storage[telegram_user_id]["backend_user_id"] = backend_user_id
        if token is not None:
            self._storage[telegram_user_id]["token"] = token
        if email is not None:
            self._storage[telegram_user_id]["email"] = email
        if password is not None:
            self._storage[telegram_user_id]["password"] = password
        if telegram_username is not None:
            self._storage[telegram_user_id]["telegram_username"] = telegram_username
        if conversation_id is not None:
            self._storage[telegram_user_id]["conversation_id"] = conversation_id
        
        self._save()

    def has_user(self, telegram_user_id: int) -> bool:
        """Проверяет, зарегистрирован ли пользователь"""
        return telegram_user_id in self._storage and "token" in self._storage[telegram_user_id]

    def get_token(self, telegram_user_id: int) -> Optional[str]:
        """Получает токен пользователя"""
        user_data = self.get(telegram_user_id)
        return user_data.get("token") if user_data else None

    def get_backend_user_id(self, telegram_user_id: int) -> Optional[int]:
        """Получает backend user_id"""
        user_data = self.get(telegram_user_id)
        return user_data.get("backend_user_id") if user_data else None

    def get_conversation_id(self, telegram_user_id: int) -> Optional[int]:
        """Получает текущий conversation_id"""
        user_data = self.get(telegram_user_id)
        return user_data.get("conversation_id") if user_data else None

    def set_conversation_id(self, telegram_user_id: int, conversation_id: Optional[int]) -> None:
        """Устанавливает текущий conversation_id"""
        self.set(telegram_user_id=telegram_user_id, conversation_id=conversation_id)



