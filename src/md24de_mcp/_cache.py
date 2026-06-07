from __future__ import annotations

import logging
import time
from dataclasses import dataclass

_log = logging.getLogger(__name__)


@dataclass
class _Entry[T]:
    value: T
    expires_at: float


class Cache[T]:
    """Thread-unsafe in-memory cache with a configurable TTL."""

    def __init__(self, ttl: float) -> None:
        self._ttl = ttl
        self._entry: _Entry[T] | None = None

    def get(self) -> T | None:
        """Return the cached value if it has not expired, otherwise ``None``."""
        entry = self._entry
        if entry is not None:
            if time.monotonic() < entry.expires_at:
                _log.debug("Cache hit (%.0fs remaining)", entry.expires_at - time.monotonic())
                return entry.value
            _log.debug("Cache expired")
            self._entry = None
        return None

    def set(self, value: T) -> None:
        """Store *value* in the cache; it will expire after the configured TTL."""
        self._entry = _Entry(value=value, expires_at=time.monotonic() + self._ttl)
        _log.debug("Cache updated (TTL %.0fs)", self._ttl)

    def clear(self) -> None:
        """Evict the cached value immediately."""
        self._entry = None
