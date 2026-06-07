# md24de-mcp — Copilot Instructions

## Project overview

Unofficial MCP (Model Context Protocol) server that wraps the
[python-md24de](https://github.com/volsch/python-md24de) library to expose
messdienst24.de utility-consumption data as MCP tools.

## Language & runtime

- Python 3.13+ only; use 3.13-compatible syntax
- All files start with `from __future__ import annotations`

## Code style

- Formatter/linter: **ruff** (`line-length = 100`, target `py313`)
- Active ruff rules: `E, F, I, N, W, UP, ANN, S, B, C4, PIE, RET, SIM` — all annotations required (`ANN`)
- Type checker: **pyright strict** — every function must be fully annotated; no `Any` unless unavoidable
- Private module files are prefixed with `_` (e.g. `_cache.py`, `_config.py`)
- Public surface is re-exported from `__init__.py` only; internals stay in `_*.py` modules

## MCP server

- MCP framework: **FastMCP** (`from mcp.server.fastmcp import FastMCP`)
- The server instance and all tools live in `server.py`
- Config and caches are initialised **lazily** on the first tool call — never at import time
- Each tool call creates a fresh `Md24deClient`, performs the minimum required requests, then closes the connection
- Results are cached in memory via `Cache[T]` from `_cache.py`

## Configuration

Runtime config is loaded from environment variables:
- `MD24DE_TENANT`, `MD24DE_USERNAME`, `MD24DE_PASSWORD` (required) — loaded in `_config.py`
- `MD24DE_TIMEOUT` (optional, default 30 s), `MD24DE_CACHE_TTL` (optional, default 1800 s) — loaded in `_config.py`
- `LOG_LEVEL` (optional, default `WARNING`) — applied in `main()` in `__init__.py`

## Models

- All data models are `@dataclass(frozen=True)` where applicable
- Use Python 3.12+ type parameter syntax (`class Foo[T]:`) instead of `Generic[T]`

## Logging

- Every `_*.py` module has `_log = logging.getLogger(__name__)` at module level
- `__init__.py` registers `logging.NullHandler()` on the `md24de_mcp` root logger
- `main()` in `__init__.py` applies `LOG_LEVEL` env var via `logging.basicConfig()` and propagates it to the `md24de` and `httpx` loggers
- Use `_log.debug(...)` for operational events (cache hits/misses, byte counts, month/year values)
- **Never log credentials** (username, password)

## Testing

- Framework: **pytest** with `pytest-cov` and `pytest-mock`
- Tests live in `tests/`
- Run tests: `pytest`
- Run type check: `pyright src/`
- Run linter: `ruff check src/ tests/`

## Build

- Build system: **hatchling**; install dev dependencies with `pip install -e ".[dev]"`
