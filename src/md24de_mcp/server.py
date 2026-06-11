from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import mcp.types as mcp_types
from mcp.server.fastmcp import FastMCP
from md24de import (
    AvailableMonth,
    ConsumptionReport,
    Md24deClient,
    MeterReading,
    MeterReport,
    ObjectInfo,
)

from ._cache import Cache
from ._config import Config

_log = logging.getLogger(__name__)

# Maps MCP LoggingLevel strings to Python logging level integers.
# "notice", "alert", "emergency" have no direct Python equivalent and are
# mapped to the nearest standard level.
_MCP_TO_PY_LOG_LEVEL: dict[mcp_types.LoggingLevel, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "notice": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "alert": logging.CRITICAL,
    "emergency": logging.CRITICAL,
}


# ---------------------------------------------------------------------------
# Lazy initialisation — _Caches is created on the first tool call so that
# importing this module does not require env vars to be set (important for
# tests and MCP introspection that import without credentials).
# A list is used as a mutable module-level container to avoid `global`.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Caches:
    config: Config
    month: Cache[AvailableMonth]
    report: Cache[tuple[AvailableMonth, ConsumptionReport]]
    pdf: Cache[bytes]


_caches: list[_Caches] = []


def _get_caches() -> _Caches:
    if not _caches:
        config = Config.from_env()
        _caches.append(
            _Caches(
                config=config,
                month=Cache(config.cache_ttl),
                report=Cache(config.cache_ttl),
                pdf=Cache(config.cache_ttl),
            )
        )
    return _caches[0]


mcp = FastMCP("md24de-mcp")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client() -> Md24deClient:
    cfg = _get_caches().config
    return Md24deClient(
        tenant=cfg.tenant,
        username=cfg.username,
        password=cfg.password,
        timeout=cfg.timeout,
    )


def _apply_log_level(py_level: int) -> None:
    """Apply *py_level* to the ``md24de_mcp``, ``md24de``, and ``httpx`` loggers.

    Mirrors the level-application logic in :func:`md24de_mcp.main` so that a
    ``logging/setLevel`` request received at runtime has the same effect as
    starting the server with the corresponding ``LOG_LEVEL`` env var.
    """
    logging.getLogger("md24de_mcp").setLevel(py_level)
    logging.getLogger("md24de").setLevel(py_level)
    httpx_level = logging.WARNING if py_level > logging.DEBUG else py_level
    logging.getLogger("httpx").setLevel(httpx_level)


def _serialize_object_info(info: ObjectInfo) -> dict[str, str]:
    return {"object_number": info.object_number, "address": info.address}


def _serialize_reading(reading: MeterReading) -> dict[str, object]:
    return {
        "year": reading.year,
        "month": reading.month,
        "your_kwh": reading.your_kwh,
        "average_kwh": reading.average_kwh,
    }


def _serialize_meter(meter: MeterReport) -> dict[str, object]:
    return {
        "your_kwh": meter.current_kwh,
        "average_kwh": meter.average_kwh,
        "vs_average": meter.vs_average.value if meter.vs_average is not None else None,
        "vs_previous_month": (
            meter.vs_previous_month.value if meter.vs_previous_month is not None else None
        ),
        "vs_previous_year": (
            meter.vs_previous_year.value if meter.vs_previous_year is not None else None
        ),
        "history": [_serialize_reading(r) for r in meter.history],
    }


def _serialize_report(month: AvailableMonth, report: ConsumptionReport) -> dict[str, object]:
    return {
        "year": month.year,
        "month": month.month,
        "object_info": _serialize_object_info(report.object_info),
        "heating": _serialize_meter(report.heating),
        "hot_water": _serialize_meter(report.hot_water),
    }


# ---------------------------------------------------------------------------
# MCP protocol handlers
# ---------------------------------------------------------------------------
# ping, resources/list, resources/read → handled automatically by FastMCP.
# Unknown methods → low-level server returns -32601 automatically.
# logging/setLevel and completion/complete require explicit registration below.


async def _handle_set_logging_level(level: mcp_types.LoggingLevel) -> None:
    py_level = _MCP_TO_PY_LOG_LEVEL.get(level, logging.WARNING)
    _log.debug("logging/setLevel: %s -> Python level %d", level, py_level)
    _apply_log_level(py_level)


async def _handle_completion(
    ref: mcp_types.PromptReference | mcp_types.ResourceTemplateReference,
    argument: mcp_types.CompletionArgument,
    context: mcp_types.CompletionContext | None,
) -> mcp_types.Completion | None:
    # This server exposes no prompts or resource templates, so there are
    # no completions to provide.  Returning None causes the framework to
    # respond with an empty completion list.
    return None


# Register handlers with the MCP framework.  Explicit call form (vs. @decorator
# syntax) keeps pyright happy because the functions are referenced as arguments.
mcp._mcp_server.set_logging_level()(_handle_set_logging_level)  # type: ignore[reportPrivateUsage]
mcp.completion()(_handle_completion)


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_last_available_month() -> dict[str, int]:
    """Return the month and year of the most recently published consumption report.

    messdienst24.de is a German utility-consumption portal that provides the legally mandated
    monthly heating and hot-water consumption report (Verbrauchsinformation) for residential
    properties. The portal publishes one report per calendar month (always a previous month,
    never the current one). This tool returns which month that currently published report
    covers.

    Call this tool when you only need to know the current reporting month without fetching
    the full report. The full report (get_consumption_report) and the PDF (save_pdf) both
    include this information as well.

    Returns:
        year:  Four-digit year of the current reporting month (e.g. 2025).
        month: Month number 1–12 of the current reporting month (e.g. 4 for April).
    """
    caches = _get_caches()
    cached = caches.month.get()
    if cached is not None:
        _log.debug("Returning cached available month %04d-%02d", cached.year, cached.month)
        return {"year": cached.year, "month": cached.month}

    _log.debug("Fetching available month from portal")
    with _make_client() as client:
        month = client.get_last_available_month()

    caches.month.set(month)
    _log.debug("Available month: %04d-%02d", month.year, month.month)
    return {"year": month.year, "month": month.month}


@mcp.tool()
def get_consumption_report() -> dict[str, object]:
    """Return the heating and hot-water consumption report from messdienst24.de.

    messdienst24.de is a German utility-consumption portal. This tool retrieves the full
    structured consumption data for your residential property. The report covers the most
    recently published month (returned as year/month at the top level) and also includes a
    history of several previous months so that trends can be analysed.

    The response includes:
        year, month:   The current reporting period (e.g. year=2025, month=4 for April 2025).
        object_info:   Property address and object number assigned by the service provider.
        heating:       Heating consumption data (see below).
        hot_water:     Hot-water consumption data (same structure as heating).

    Each meter section (heating / hot_water) contains:
        your_kwh:          Your consumption for the current reporting month in kWh equivalent.
        average_kwh:       Average consumption of comparable households in kWh equivalent.
        vs_average:        How your usage compares to similar households this month.
                           "less" = you used less, "more" = you used more, "equal" = same.
                           null if the comparison is unavailable.
        vs_previous_month: How your usage compares to the previous month (same values).
                           null if unavailable.
        vs_previous_year:  How your usage compares to the same month last year (same values).
                           null if unavailable.
        history:           List of monthly readings for several past months, newest first.
                           Each entry has year, month, your_kwh, average_kwh.
                           history[0] always corresponds to the current reporting month.
    """
    caches = _get_caches()
    cached = caches.report.get()
    if cached is not None:
        cached_month, cached_report = cached
        _log.debug(
            "Returning cached consumption report for %04d-%02d",
            cached_month.year,
            cached_month.month,
        )
        return _serialize_report(cached_month, cached_report)

    _log.debug("Fetching consumption report from portal")
    with _make_client() as client:
        month = client.get_last_available_month()
        report = client.get_consumption_report()

    caches.month.set(month)
    caches.report.set((month, report))
    _log.debug("Consumption report fetched for %04d-%02d", month.year, month.month)
    return _serialize_report(month, report)


@mcp.tool()
def save_pdf(directory: str = "~/Downloads") -> dict[str, object]:
    """Download the monthly consumption PDF and save it to disk.

    This is the legally mandated *unterjährige Verbrauchsinformation* (UVI) document —
    a German statutory heating-cost information notice that property owners are required
    to provide to tenants under §6a HeizkostenV. The document is generated by the
    messdienst24.de portal and covers the same month returned by get_last_available_month.

    Use this tool when the user wants to save, view, or forward the actual PDF document
    rather than just reading the structured consumption figures.

    Args:
        directory: Directory where the PDF will be saved. Defaults to ~/Downloads.
                   The filename is set automatically to e.g. "verbrauch-2025-04.pdf".

    Returns:
        saved_to:    Full path of the saved file.
        filename:    The filename used, e.g. "verbrauch-2025-04.pdf".
        year, month: The period the document covers.
        size_bytes:  Size of the saved PDF in bytes.
    """
    caches = _get_caches()
    cached_pdf = caches.pdf.get()
    cached_month = caches.month.get()

    if cached_pdf is not None and cached_month is not None:
        _log.debug("Using cached PDF for %04d-%02d", cached_month.year, cached_month.month)
        pdf_bytes, month = cached_pdf, cached_month
    else:
        _log.debug("Fetching PDF from portal")
        with _make_client() as client:
            month = client.get_last_available_month()
            pdf_bytes = client.get_pdf()
        caches.month.set(month)
        caches.pdf.set(pdf_bytes)
        _log.debug("PDF fetched: %d bytes for %04d-%02d", len(pdf_bytes), month.year, month.month)

    filename = f"verbrauch-{month.year}-{month.month:02d}.pdf"
    dest = Path(directory).expanduser() / filename
    dest.write_bytes(pdf_bytes)
    _log.debug("PDF saved to %s", dest)
    return {
        "saved_to": str(dest),
        "filename": filename,
        "year": month.year,
        "month": month.month,
        "size_bytes": len(pdf_bytes),
    }
