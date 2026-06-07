from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from md24de import (
    AvailableMonth,
    Comparison,
    ConsumptionReport,
    MeterReading,
    MeterReport,
    ObjectInfo,
)
from pytest_mock import MockerFixture

import md24de_mcp.server as server_module
from md24de_mcp._config import Config
from md24de_mcp.server import (
    _serialize_meter,
    _serialize_object_info,
    _serialize_reading,
    _serialize_report,
    get_consumption_report,
    get_last_available_month,
    save_pdf,
)

_TEST_CONFIG = Config(tenant="xy", username="user", password="pass", timeout=10.0, cache_ttl=60.0)
_PDF_BYTES = b"%PDF-1.4 test"


@pytest.fixture(autouse=True)
def reset_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the module-level cache container before every test."""
    monkeypatch.setattr(server_module, "_caches", [])


@pytest.fixture
def mock_config(mocker: MockerFixture) -> Config:
    mocker.patch("md24de_mcp.server.Config.from_env", return_value=_TEST_CONFIG)
    return _TEST_CONFIG


@pytest.fixture
def mock_client(
    mocker: MockerFixture,
    available_month: AvailableMonth,
    consumption_report: ConsumptionReport,
) -> MagicMock:
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get_last_available_month.return_value = available_month
    client.get_consumption_report.return_value = consumption_report
    client.get_pdf.return_value = _PDF_BYTES
    mocker.patch("md24de_mcp.server.Md24deClient", return_value=client)
    return client


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def test_serialize_object_info() -> None:
    info = ObjectInfo(object_number="OBJ-001", address="Main St 1")
    result = _serialize_object_info(info)
    assert result == {"object_number": "OBJ-001", "address": "Main St 1"}


def test_serialize_reading() -> None:
    reading = MeterReading(year=2025, month=4, your_kwh=100.0, average_kwh=120.0)
    result = _serialize_reading(reading)
    assert result == {"year": 2025, "month": 4, "your_kwh": 100.0, "average_kwh": 120.0}


def test_serialize_meter_with_comparisons(meter_report: MeterReport) -> None:
    result = _serialize_meter(meter_report)
    assert result["your_kwh"] == 123.4
    assert result["average_kwh"] == 150.0
    assert result["vs_average"] == "less"
    assert result["vs_previous_month"] == "more"
    assert result["vs_previous_year"] is None
    assert len(result["history"]) == 1  # type: ignore[arg-type]


def test_serialize_meter_equal_comparison(meter_reading: MeterReading) -> None:
    report = MeterReport(
        current_kwh=60.0,
        average_kwh=60.0,
        vs_average=Comparison.EQUAL,
        vs_previous_month=None,
        vs_previous_year=None,
        history=(meter_reading,),
    )
    result = _serialize_meter(report)
    assert result["vs_average"] == "equal"
    assert result["vs_previous_month"] is None


def test_serialize_meter_all_null_comparisons(meter_reading: MeterReading) -> None:
    report = MeterReport(
        current_kwh=50.0,
        average_kwh=60.0,
        vs_average=None,
        vs_previous_month=None,
        vs_previous_year=None,
        history=(meter_reading,),
    )
    result = _serialize_meter(report)
    assert result["vs_average"] is None
    assert result["vs_previous_month"] is None
    assert result["vs_previous_year"] is None


def test_serialize_report_includes_year_month(
    available_month: AvailableMonth,
    consumption_report: ConsumptionReport,
) -> None:
    result = _serialize_report(available_month, consumption_report)
    assert result["year"] == 2025
    assert result["month"] == 4
    assert "object_info" in result
    assert "heating" in result
    assert "hot_water" in result


def test_build_pdf_filename() -> None:
    # verify filename format used by save_pdf
    assert f"verbrauch-{2025}-{4:02d}.pdf" == "verbrauch-2025-04.pdf"


# ---------------------------------------------------------------------------
# get_last_available_month
# ---------------------------------------------------------------------------


def test_get_last_available_month_cache_miss(
    mock_config: Config,
    mock_client: MagicMock,
) -> None:
    result = get_last_available_month()
    assert result == {"year": 2025, "month": 4}
    mock_client.get_last_available_month.assert_called_once()


def test_get_last_available_month_cache_hit(
    mock_config: Config,
    mock_client: MagicMock,
) -> None:
    get_last_available_month()
    result = get_last_available_month()
    assert result == {"year": 2025, "month": 4}
    mock_client.get_last_available_month.assert_called_once()  # only fetched once


def test_get_last_available_month_uses_config_credentials(
    mock_config: Config,
    mock_client: MagicMock,
    mocker: MockerFixture,
) -> None:
    client_cls = mocker.patch("md24de_mcp.server.Md24deClient", return_value=mock_client)
    get_last_available_month()
    client_cls.assert_called_once_with(
        tenant="xy", username="user", password="pass", timeout=10.0
    )


# ---------------------------------------------------------------------------
# get_consumption_report
# ---------------------------------------------------------------------------


def test_get_consumption_report_cache_miss(
    mock_config: Config,
    mock_client: MagicMock,
) -> None:
    result = get_consumption_report()
    assert result["year"] == 2025
    assert result["month"] == 4
    assert "heating" in result
    assert "hot_water" in result
    mock_client.get_consumption_report.assert_called_once()


def test_get_consumption_report_cache_hit(
    mock_config: Config,
    mock_client: MagicMock,
) -> None:
    get_consumption_report()
    get_consumption_report()
    mock_client.get_consumption_report.assert_called_once()


def test_get_consumption_report_also_caches_month(
    mock_config: Config,
    mock_client: MagicMock,
) -> None:
    get_consumption_report()
    # Month should now be cached — get_last_available_month must not hit the portal
    get_last_available_month()
    mock_client.get_last_available_month.assert_called_once()  # called inside report, not again


# ---------------------------------------------------------------------------
# save_pdf
# ---------------------------------------------------------------------------


def test_save_pdf_cache_miss(
    mock_config: Config,
    mock_client: MagicMock,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = save_pdf(directory=tmp)
        assert result["year"] == 2025
        assert result["month"] == 4
        assert result["filename"] == "verbrauch-2025-04.pdf"
        assert result["size_bytes"] == len(_PDF_BYTES)
        saved = Path(str(result["saved_to"]))
        assert saved.read_bytes() == _PDF_BYTES
    mock_client.get_pdf.assert_called_once()


def test_save_pdf_cache_hit(
    mock_config: Config,
    mock_client: MagicMock,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        save_pdf(directory=tmp)
        save_pdf(directory=tmp)
    mock_client.get_pdf.assert_called_once()


def test_save_pdf_partial_cache_refetches(
    mock_config: Config,
    mock_client: MagicMock,
) -> None:
    # Only month is cached (not pdf) — must still fetch from portal
    get_last_available_month()
    with tempfile.TemporaryDirectory() as tmp:
        save_pdf(directory=tmp)
    mock_client.get_pdf.assert_called_once()


def test_save_pdf_also_caches_month(
    mock_config: Config,
    mock_client: MagicMock,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        save_pdf(directory=tmp)
    # Month should now be cached — get_last_available_month must not hit the portal again
    get_last_available_month()
    mock_client.get_last_available_month.assert_called_once()
