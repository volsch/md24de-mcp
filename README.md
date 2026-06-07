# md24de-mcp

[![Latest release](https://img.shields.io/github/v/release/volsch/md24de-mcp?label=latest)](https://github.com/volsch/md24de-mcp/releases/latest)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=volsch_md24de-mcp&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=volsch_md24de-mcp)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=volsch_md24de-mcp&metric=coverage)](https://sonarcloud.io/summary/new_code?id=volsch_md24de-mcp)

Unofficial [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for the
[messdienst24.de](https://messdienst24.de) utility-consumption portal.

Wraps [python-md24de](https://github.com/volsch/python-md24de) to expose heating and
hot-water consumption data as MCP tools that any MCP-compatible AI client can invoke.

> **Disclaimer** — This project is not affiliated with, endorsed by, or in any way officially
> connected with messdienst24.de or its operators. Use at your own risk.

---

## Tools

| Tool | Description |
|---|---|
| `get_last_available_month` | Returns the year/month for which the portal currently provides data |
| `get_consumption_report` | Returns the full heating and hot-water consumption report |
| `save_pdf` | Downloads the monthly consumption PDF and saves it to disk |

### `get_last_available_month`

Returns `{ "year": int, "month": int }`.

### `get_consumption_report`

Returns structured consumption data with the following shape:

```json
{
  "year": 2025,
  "month": 4,
  "object_info": { "object_number": "…", "address": "…" },
  "heating": {
    "your_kwh": 123.4,
    "average_kwh": 150.0,
    "vs_average": "less",
    "vs_previous_month": "more",
    "vs_previous_year": null,
    "history": [
      { "year": 2025, "month": 4, "your_kwh": 123.4, "average_kwh": 150.0 },
      { "year": 2025, "month": 3, "your_kwh": 140.0, "average_kwh": 160.0 }
    ]
  },
  "hot_water": { "…": "…" }
}
```

Comparison values are `"less"`, `"more"`, `"equal"`, or `null` when unavailable.

### `save_pdf`

Saves the PDF to disk and returns:

```json
{
  "saved_to": "/Users/you/Downloads/verbrauch-2025-04.pdf",
  "filename": "verbrauch-2025-04.pdf",
  "year": 2025,
  "month": 4,
  "size_bytes": 123456
}
```

The optional `directory` parameter controls where the file is saved (default: `~/Downloads`).

---

## Example prompts

Once connected to Claude Desktop, you can ask:

- *"How much heating energy did I use last month?"*
- *"Am I using more or less heating than comparable households?"*
- *"Show me my hot-water consumption trend over the past months."*
- *"Compare my heating usage to last year's same month."*
- *"Give me a summary of my energy consumption."*
- *"Save my monthly consumption PDF to my Downloads folder."*
- *"Save my monthly consumption PDF to my Desktop."*
- *"Which month's data is currently available on messdienst24.de?"*

---

## Client lifecycle and caching

Each tool creates a fresh `Md24deClient`, performs the minimum required requests, then
closes the connection. This avoids server-side session timeouts for long-running processes.

Results are cached in memory for a configurable TTL (default 30 minutes):

| Tool | Caches |
|---|---|
| `get_last_available_month` | available month |
| `get_consumption_report` | available month + consumption report |
| `save_pdf` | available month + PDF bytes |

---

## Configuration

All configuration is provided via environment variables.

| Variable | Required | Default | Description |
|---|---|---|---|
| `MD24DE_TENANT` | ✓ | — | Short portal ID (the `md=` part of the login URL, e.g. `xy`) |
| `MD24DE_USERNAME` | ✓ | — | Portal login username |
| `MD24DE_PASSWORD` | ✓ | — | Portal login password |
| `MD24DE_TIMEOUT` | | `30.0` | HTTP request timeout in seconds |
| `MD24DE_CACHE_TTL` | | `1800` | Cache time-to-live in seconds |
| `LOG_LEVEL` | | `WARNING` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## Installation

This package is not published on PyPI. The recommended way to install it for use with
Claude Desktop or other MCP clients is **[pipx](https://pipx.pypa.io)**, which installs
the `md24de-mcp` command globally while keeping its dependencies isolated:

```bash
pipx install "git+https://github.com/volsch/md24de-mcp.git@vX.Y.Z"
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install "git+https://github.com/volsch/md24de-mcp.git@vX.Y.Z"
```

Both put `md24de-mcp` on your PATH so MCP clients can launch it by name.

To upgrade to a newer version, replace `vX.Y.Z` and run `pipx upgrade md24de-mcp` or
`uv tool upgrade md24de-mcp`.

---

## Running

```bash
export MD24DE_TENANT=xy
export MD24DE_USERNAME=your_user
export MD24DE_PASSWORD=your_pass

md24de-mcp
```

### MCP client configuration

#### Claude Desktop

**1. Install the server** (see [Installation](#installation) above, e.g. with pipx):

```bash
pipx install "git+https://github.com/volsch/md24de-mcp.git@vX.Y.Z"
```

**2. Add it to the Claude Desktop config.**
Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "md24de": {
      "command": "md24de-mcp",
      "env": {
        "MD24DE_TENANT": "xy",
        "MD24DE_USERNAME": "your_user",
        "MD24DE_PASSWORD": "your_pass"
      }
    }
  }
}
```

Replace `xy`, `your_user`, and `your_pass` with your actual messdienst24.de credentials.
The tenant ID is the `md=` value from your portal login URL (e.g. `https://messdienst24.de/?md=xy`).

**3. Restart Claude Desktop.**

**4. Verify the connection.**
A 🔧 icon in the chat input bar confirms the server is connected.
Click it to see the list of available tools (`get_last_available_month`, `get_consumption_report`, `save_pdf`).

**5. Try an example prompt** (see [Example prompts](#example-prompts) above), e.g.:
> *"How much heating energy did I use last month?"*

## Logging

The server uses Python's standard `logging` module under the `md24de_mcp` logger hierarchy
and registers a `NullHandler` so no output appears unless the calling process configures
logging explicitly.

Set the `LOG_LEVEL` environment variable to control verbosity:

```json
{
  "mcpServers": {
    "md24de": {
      "command": "md24de-mcp",
      "env": {
        "MD24DE_TENANT": "xy",
        "MD24DE_USERNAME": "your_user",
        "MD24DE_PASSWORD": "your_pass",
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

Debug messages include cache hits/misses, available month/year values, and byte counts.
The underlying `md24de` library also emits debug messages (HTTP status codes, parsed dates).
**Credentials (username, password) are never written to any log message.**

---

## Development

```bash
git clone https://github.com/volsch/md24de-mcp.git
cd md24de-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest
```

Type-check:

```bash
pyright src/
```

Lint and format:

```bash
ruff check src/ tests/
ruff format src/ tests/
```

---

## Legal

### Legal context for the data

The monthly consumption report accessed through this server is the *unterjährige
Verbrauchsinformation* (UVI) — a legally mandated document under §6a of the German
Heating Cost Ordinance (*Heizkostenverordnung*, HeizkostenV). Under §6b HeizkostenV,
consumption data may only be collected and used for billing purposes and to fulfil the
legal information obligations. This server retrieves your own data from the portal
provided for exactly that purpose.

### Unofficial project

This server is **not** an official product of messdienst24.de. It was built by observing the
portal's web interface for personal and educational use. It does not circumvent any technical
protection measures and only uses credentials that the account holder provides themselves.

### Credentials and privacy

Your username and password are passed directly to the messdienst24.de servers over HTTPS via
the underlying [python-md24de](https://github.com/volsch/python-md24de) library.
This server does not store or log credentials. However, any direct or indirect dependency —
such as HTTP client internals, logging back-ends, or network proxies configured in your
environment — is outside this server's control and may handle the data differently.

Consumption data fetched from the portal is held in memory only for the duration of the cache
TTL and is never written to disk by this server.

### No warranty

The portal's HTML structure can change at any time without notice, which may break the
underlying library. The software is provided "as is" — see the [LICENSE](LICENSE) for full
terms.

### Terms of service

Before using this server, ensure your use complies with the messdienst24.de terms of service.
Automated access may be restricted by those terms.

## License

[MIT](LICENSE) © 2026 Volker Schmidt
