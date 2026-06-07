from __future__ import annotations

import pytest

from md24de_mcp._config import Config


def test_from_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MD24DE_TENANT", "xy")
    monkeypatch.setenv("MD24DE_USERNAME", "user")
    monkeypatch.setenv("MD24DE_PASSWORD", "secret")
    monkeypatch.delenv("MD24DE_TIMEOUT", raising=False)
    monkeypatch.delenv("MD24DE_CACHE_TTL", raising=False)

    cfg = Config.from_env()

    assert cfg.tenant == "xy"
    assert cfg.username == "user"
    assert cfg.password == "secret"
    assert cfg.timeout == 30.0
    assert cfg.cache_ttl == 1800.0


def test_from_env_optional_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MD24DE_TENANT", "xy")
    monkeypatch.setenv("MD24DE_USERNAME", "user")
    monkeypatch.setenv("MD24DE_PASSWORD", "secret")
    monkeypatch.setenv("MD24DE_TIMEOUT", "15.5")
    monkeypatch.setenv("MD24DE_CACHE_TTL", "300")

    cfg = Config.from_env()

    assert cfg.timeout == 15.5
    assert cfg.cache_ttl == 300.0


def test_from_env_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MD24DE_TENANT", "  xy  ")
    monkeypatch.setenv("MD24DE_USERNAME", "  user  ")
    monkeypatch.setenv("MD24DE_PASSWORD", "  secret  ")

    cfg = Config.from_env()

    assert cfg.tenant == "xy"
    assert cfg.username == "user"
    assert cfg.password == "secret"


def test_from_env_missing_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MD24DE_TENANT", raising=False)
    monkeypatch.setenv("MD24DE_USERNAME", "user")
    monkeypatch.setenv("MD24DE_PASSWORD", "secret")

    with pytest.raises(RuntimeError, match="MD24DE_TENANT"):
        Config.from_env()


def test_from_env_missing_username(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MD24DE_TENANT", "xy")
    monkeypatch.delenv("MD24DE_USERNAME", raising=False)
    monkeypatch.setenv("MD24DE_PASSWORD", "secret")

    with pytest.raises(RuntimeError, match="MD24DE_USERNAME"):
        Config.from_env()


def test_from_env_missing_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MD24DE_TENANT", "xy")
    monkeypatch.setenv("MD24DE_USERNAME", "user")
    monkeypatch.delenv("MD24DE_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="MD24DE_PASSWORD"):
        Config.from_env()


def test_from_env_missing_all_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MD24DE_TENANT", raising=False)
    monkeypatch.delenv("MD24DE_USERNAME", raising=False)
    monkeypatch.delenv("MD24DE_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="MD24DE_TENANT"):
        Config.from_env()
