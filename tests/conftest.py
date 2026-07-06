from __future__ import annotations

import pytest
from md24de import (
    AvailableMonth,
    Comparison,
    ConsumptionReport,
    MeterReading,
    MeterReport,
    ObjectInfo,
)


@pytest.fixture
def available_month() -> AvailableMonth:
    return AvailableMonth(year=2025, month=4)


@pytest.fixture
def meter_reading() -> MeterReading:
    return MeterReading(year=2025, month=4, your_kwh=111.1, average_kwh=222.2)


@pytest.fixture
def meter_report(meter_reading: MeterReading) -> MeterReport:
    return MeterReport(
        current_kwh=111.1,
        average_kwh=222.2,
        vs_average=Comparison.LESS,
        vs_previous_month=Comparison.MORE,
        vs_previous_year=None,
        history=(meter_reading,),
    )


@pytest.fixture
def consumption_report(meter_report: MeterReport) -> ConsumptionReport:
    return ConsumptionReport(
        object_info=ObjectInfo(
            object_number="OBJ-001", address="Musterstraße 1, 12345 Musterstadt"
        ),
        heating=meter_report,
        hot_water=meter_report,
    )
