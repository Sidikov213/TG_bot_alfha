from collections import deque
from typing import Deque, Dict, List, Tuple

class ConversationMemory:
    def __init__(self, max_messages: int = 8):
        self.max_messages = max_messages
        self._store: Dict[int, Deque[Tuple[str, str]]] = {}

    def add(self, user_id: int, role: str, content: str) -> None:
        if user_id not in self._store:
            self._store[user_id] = deque(maxlen=self.max_messages)
        self._store[user_id].append((role, content))

    def get(self, user_id: int) -> List[Tuple[str, str]]:
        return list(self._store.get(user_id, deque()))

    def clear(self, user_id: int) -> None:
        if user_id in self._store:
            self._store[user_id].clear()
