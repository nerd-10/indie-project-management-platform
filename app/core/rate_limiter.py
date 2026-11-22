import threading
import time
from collections import defaultdict, deque
from collections.abc import Hashable
from uuid import UUID, uuid4


class SlidingWindowRateLimiter:
    def __init__(
        self,
        max_attempts: int,
        window_seconds: int,
    ) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be greater than zero")

        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than zero")

        self.max_attempts = max_attempts
        self.window_seconds = window_seconds

        self._attempts: dict[Hashable, deque[tuple[float, UUID]]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._cleanup_interval_seconds = 60
        self._last_cleanup = time.monotonic()

    def try_acquire(self, key: Hashable) -> UUID | None:
        reservation_id = uuid4()

        with self._lock:
            now = time.monotonic()
            if now - self._last_cleanup >= self._cleanup_interval_seconds:
                self._cleanup_expired(now)
                self._last_cleanup = now

            attempts = self._attempts[key]
            self._remove_expired(attempts, now)

            if len(attempts) >= self.max_attempts:
                return None

            attempts.append((now, reservation_id))
            return reservation_id

    def release(self, key: Hashable, reservation_id: UUID) -> None:
        with self._lock:
            attempts = self._attempts.get(key)

            if not attempts:
                return

            for attempt in attempts:
                if attempt[1] == reservation_id:
                    attempts.remove(attempt)
                    break

            if not attempts:
                self._attempts.pop(key, None)

    def clear(self, key: Hashable) -> None:
        with self._lock:
            self._attempts.pop(key, None)

    def _cleanup_expired(self, now: float) -> None:
        expired_keys = []
        for key, attempts in self._attempts.items():
            self._remove_expired(attempts, now)

            if not attempts:
                expired_keys.append(key)

        for key in expired_keys:
            del self._attempts[key]

    def cleanup(self) -> None:
        now = time.monotonic()

        with self._lock:
            self._cleanup_expired(now)
            self._last_cleanup = now

    def get_retry_after(self, key: Hashable) -> int:
        now = time.monotonic()

        with self._lock:
            attempts = self._attempts.get(key)

            if not attempts:
                return 0

            self._remove_expired(attempts, now)

            if not attempts:
                self._attempts.pop(key, None)
                return 0

            if len(attempts) < self.max_attempts:
                return 0

            remaining = self.window_seconds - (now - attempts[0][0])
            return max(1, int(remaining + 0.999999))

    def _remove_expired(
        self,
        attempts: deque[tuple[float, UUID]],
        now: float,
    ) -> None:
        while attempts and now - attempts[0][0] >= self.window_seconds:
            attempts.popleft()