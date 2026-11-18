"""Giới hạn đăng nhập sai (chống dò mật khẩu). Lưu trong bộ nhớ của tiến trình."""
import threading
import time
from collections import defaultdict, deque


class FailureLimiter:
    def __init__(self, max_failures: int = 5, window_seconds: int = 900):
        self.max_failures = max_failures
        self.window = window_seconds
        self._events: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque:
        events = self._events[key]
        while events and now - events[0] > self.window:
            events.popleft()
        if not events:
            self._events.pop(key, None)
        return events

    def retry_after(self, key: str) -> int:
        """Số giây phải chờ; 0 nếu chưa bị khóa."""
        with self._lock:
            now = time.monotonic()
            events = self._prune(key, now)
            if len(events) >= self.max_failures:
                return int(self.window - (now - events[0])) + 1
            return 0

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._events[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)


login_limiter = FailureLimiter()
