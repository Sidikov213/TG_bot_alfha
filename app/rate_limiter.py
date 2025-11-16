import time
from collections import deque
from typing import Deque, Dict

class RateLimiter:
    def __init__(self, per_minute: int = 20):
        self.per_minute = per_minute
        self._hits: Dict[int, Deque[float]] = {}

    def allow(self, user_id: int) -> bool:
        now = time.time()
        window_start = now - 60
        q = self._hits.setdefault(user_id, deque())
        # purge old
        while q and q[0] < window_start:
            q.popleft()
        if len(q) < self.per_minute:
            q.append(now)
            return True
        return False
