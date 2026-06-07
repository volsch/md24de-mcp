from __future__ import annotations

import logging
import os
from dataclasses import dataclass

_log = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0
_DEFAULT_CACHE_TTL = 1800.0  # 30 minutes


@dataclass(frozen=True)
class Config:
    """Runtime configuration loaded from environment variables."""

    tenant: str
    """Short portal identifier (the ``md=`` part of the login URL)."""

    username: str
    """Portal login username."""

    password: str
    """Portal login password."""

    timeout: float
    """HTTP request timeout in seconds."""

    cache_ttl: float
    """Cache time-to-live in seconds."""

    @classmethod
    def from_env(cls) -> Config:
        """Build a :class:`Config` from environment variables.

        Required:
            ``MD24DE_TENANT``, ``MD24DE_USERNAME``, ``MD24DE_PASSWORD``

        Optional:
            ``MD24DE_TIMEOUT`` (default: 30 s),
            ``MD24DE_CACHE_TTL`` (default: 1800 s / 30 min)
        """
        tenant = os.environ.get("MD24DE_TENANT", "").strip()
        username = os.environ.get("MD24DE_USERNAME", "").strip()
        password = os.environ.get("MD24DE_PASSWORD", "").strip()

        missing = [name for name, val in (
            ("MD24DE_TENANT", tenant),
            ("MD24DE_USERNAME", username),
            ("MD24DE_PASSWORD", password),
        ) if not val]
        if missing:
            raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")

        timeout = float(os.environ.get("MD24DE_TIMEOUT", str(_DEFAULT_TIMEOUT)))
        cache_ttl = float(os.environ.get("MD24DE_CACHE_TTL", str(_DEFAULT_CACHE_TTL)))

        _log.debug(
            "Config loaded: tenant=%s timeout=%.1fs cache_ttl=%.0fs",
            tenant,
            timeout,
            cache_ttl,
        )
        return cls(
            tenant=tenant,
            username=username,
            password=password,
            timeout=timeout,
            cache_ttl=cache_ttl,
        )
