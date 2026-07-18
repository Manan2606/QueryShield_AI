from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock


class AuthRateLimitExceeded(RuntimeError):
    pass


@dataclass
class _AttemptBucket:
    attempts: list[datetime] = field(default_factory=list)


class AuthRateLimiter:
    def __init__(self, max_attempts: int = 10, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window = timedelta(seconds=window_seconds)
        self._attempts: dict[str, _AttemptBucket] = {}
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = datetime.utcnow()
        cutoff = now - self.window
        normalized_key = key.strip().lower()
        with self._lock:
            bucket = self._attempts.setdefault(normalized_key, _AttemptBucket())
            bucket.attempts = [
                attempt for attempt in bucket.attempts if attempt >= cutoff
            ]
            if len(bucket.attempts) >= self.max_attempts:
                raise AuthRateLimitExceeded(
                    "Too many authentication attempts. Please wait a few minutes and try again."
                )
            bucket.attempts.append(now)

    def reset(self, key: str) -> None:
        normalized_key = key.strip().lower()
        with self._lock:
            self._attempts.pop(normalized_key, None)


auth_rate_limiter = AuthRateLimiter()
