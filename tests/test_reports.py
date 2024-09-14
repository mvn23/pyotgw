"""Tests for pyotgw/reports.py."""

from collections.abc import Callable

import pytest

import pyotgw.vars as v
from pyotgw.reports import _CONVERSIONS, convert_report_response_to_status_update
from pyotgw.types import (
    OpenThermDataSource,
    OpenThermGatewayOpMode,
    OpenThermGPIOMode,
    OpenThermHotWaterOverrideMode,
    OpenThermLEDMode,
    OpenThermReport,
    OpenThermResetCause,
    OpenThermSetpointOverrideMode,
    OpenThermSmartPowerMode,
    OpenThermTemperatureSensorFunction,
    OpenThermThermostatDetection,
    OpenThermVoltageReferenceLevel,
)

REPORT_TEST_PARAMETERS = ("report", "response", "expected_dict")

REPORT_TEST_VALUES = [
    (
        OpenThermReport.ABOUT,
        "Test version 1.0",
        {OpenThermDataSource.GATEWAY: {v.OTGW_ABOUT: "Test version 1.0"}},
    ),
    (
        OpenThermReport.BUILD,
        "17:52 12-03-2023",
        {OpenThermDataSource.GATEWAY: {v.OTGW_BUILD: "17:52 12-03-2023"}},
    ),
    (
        OpenThermReport.CLOCK_SPEED,
        "4 MHz",
        {OpenThermDataSource.GATEWAY: {v.OTGW_CLOCKMHZ: "4 MHz"}},
    ),
    (
        OpenThermReport.TEMP_SENSOR_FUNCTION,
        "R",
        {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_TEMP_SENSOR: OpenThermTemperatureSensorFunction.RETURN_WATER_TEMPERATURE
            }
        },
    ),
    (
        OpenThermReport.GPIO_MODES,
        "46",
        {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_GPIO_A: OpenThermGPIOMode.LED_F,
                v.OTGW_GPIO_B: OpenThermGPIOMode.AWAY,
            },
        },
    ),
    (
        OpenThermReport.GPIO_STATES,
        "10",
        {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_GPIO_A_STATE: 1,
                v.OTGW_GPIO_B_STATE: 0,
            }
        },
    ),
    (
        OpenThermReport.LED_MODES,
        "HWCEMP",
        {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_LED_A: OpenThermLEDMode.CENTRAL_HEATING_ON,
                v.OTGW_LED_B: OpenThermLEDMode.HOT_WATER_ON,
                v.OTGW_LED_C: OpenThermLEDMode.COMFORT_MODE_ON,
                v.OTGW_LED_D: OpenThermLEDMode.TX_ERROR_DETECTED,
                v.OTGW_LED_E: OpenThermLEDMode.BOILER_MAINTENANCE_REQUIRED,
                v.OTGW_LED_F: OpenThermLEDMode.RAISED_POWER_MODE_ACTIVE,
            },
        },
    ),
    (
        OpenThermReport.OP_MODE,
        "G",
        {OpenThermDataSource.GATEWAY: {v.OTGW_MODE: OpenThermGatewayOpMode.GATEWAY}},
    ),
    (
        OpenThermReport.SETPOINT_OVERRIDE,
        "c17.25",
        {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_SETP_OVRD_MODE: OpenThermSetpointOverrideMode.CONSTANT,
            },
            OpenThermDataSource.THERMOSTAT: {
                v.DATA_ROOM_SETPOINT_OVRD: 17.25,
            },
        },
    ),
    (
        OpenThermReport.SMART_PWR_MODE,
        "Medium power",
        {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_SMART_PWR: OpenThermSmartPowerMode.MEDIUM
            }
        },
    ),
    (
        OpenThermReport.RESET_CAUSE,
        "B",
        {OpenThermDataSource.GATEWAY: {v.OTGW_RST_CAUSE: OpenThermResetCause.BROWNOUT}},
    ),
    (
        OpenThermReport.THERMOSTAT_DETECTION_STATE,
        "C",
        {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_THRM_DETECT: OpenThermThermostatDetection.CELCIA_20
            }
        },
    ),
    (
        OpenThermReport.SETBACK_TEMPERATURE,
        "15.1",
        {OpenThermDataSource.GATEWAY: {v.OTGW_SB_TEMP: 15.1}},
    ),
    (
        OpenThermReport.TWEAKS,
        "10",
        {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_IGNORE_TRANSITIONS: 1,
                v.OTGW_OVRD_HB: 0,
            }
        },
    ),
    (
        OpenThermReport.VREF,
        "6",
        {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_VREF: OpenThermVoltageReferenceLevel.LEVEL_6
            }
        },
    ),
    (
        OpenThermReport.DHW,
        "1",
        {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_DHW_OVRD: OpenThermHotWaterOverrideMode.FORCE_ON
            }
        },
    ),
]


def test_conversion_dict() -> None:
    """Test the structure of the _CONVERSIONS dict."""
    for key, value in _CONVERSIONS.items():
        assert isinstance(key, OpenThermReport)
        assert isinstance(value, Callable)


@pytest.mark.parametrize(
    REPORT_TEST_PARAMETERS,
    REPORT_TEST_VALUES,
)
def test_command_conversion_ok(
    report: OpenThermReport,
    response: str,
    expected_dict: dict[OpenThermDataSource, dict],
) -> None:
    """Test command conversions when all goes well."""
    assert convert_report_response_to_status_update(report, response) == expected_dict


@pytest.mark.parametrize(
    ("report", "response"),
    [
        (OpenThermReport.GPIO_STATES, "cant_be_cast_to_int"),
        (OpenThermReport.RESET_CAUSE, "not_a_valid_cause"),
        ("not_a_command", None),
    ],
)
def test_command_conversion_not_ok(
    report: OpenThermReport,
    response: str,
) -> None:
    """Test command conversion with invalid input."""
    assert convert_report_response_to_status_update(report, response) is None
