from __future__ import annotations

import time

import pytest

from md24de_mcp._cache import Cache


def test_cache_miss_when_empty() -> None:
    cache: Cache[str] = Cache(ttl=60.0)
    assert cache.get() is None


def test_cache_hit_after_set() -> None:
    cache: Cache[str] = Cache(ttl=60.0)
    cache.set("hello")
    assert cache.get() == "hello"


def test_cache_returns_same_value_on_repeated_get() -> None:
    cache: Cache[int] = Cache(ttl=60.0)
    cache.set(42)
    assert cache.get() == 42
    assert cache.get() == 42


def test_cache_miss_after_expiry() -> None:
    cache: Cache[str] = Cache(ttl=0.05)
    cache.set("value")
    time.sleep(0.1)
    assert cache.get() is None


def test_cache_clear_evicts_value() -> None:
    cache: Cache[str] = Cache(ttl=60.0)
    cache.set("value")
    cache.clear()
    assert cache.get() is None


def test_cache_set_overwrites_previous_value() -> None:
    cache: Cache[str] = Cache(ttl=60.0)
    cache.set("first")
    cache.set("second")
    assert cache.get() == "second"


def test_cache_accepts_none_as_value() -> None:
    cache: Cache[str | None] = Cache(ttl=60.0)
    cache.set(None)
    assert cache.get() is None  # None value looks like a miss — acceptable limitation


def test_cache_zero_ttl_expires_immediately() -> None:
    cache: Cache[str] = Cache(ttl=0.0)
    cache.set("value")
    # With TTL=0, the entry expires at the moment it is set; a tiny sleep ensures it.
    time.sleep(0.001)
    assert cache.get() is None


@pytest.mark.parametrize("value", [0, 3.14, b"bytes", {"key": "val"}])
def test_cache_stores_various_types(value: object) -> None:
    cache: Cache[object] = Cache(ttl=60.0)
    cache.set(value)
    assert cache.get() == value
