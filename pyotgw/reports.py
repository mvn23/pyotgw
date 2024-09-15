"""Define how report responses should be turned into status dict updates."""

from collections.abc import Callable

from . import vars as v
from .types import (
    OpenThermDataSource,
    OpenThermGatewayOpMode,
    OpenThermGPIOMode,
    OpenThermLEDMode,
    OpenThermReport,
    OpenThermResetCause,
    OpenThermSetpointOverrideMode,
    OpenThermSmartPowerMode,
    OpenThermTemperatureSensorFunction,
    OpenThermThermostatDetection,
    OpenThermVoltageReferenceLevel,
)

_CONVERSIONS: dict[OpenThermReport, Callable] = {
    OpenThermReport.ABOUT: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_ABOUT: response,
            },
        }
    ),
    OpenThermReport.BUILD: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_BUILD: response,
            },
        }
    ),
    OpenThermReport.CLOCK_SPEED: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_CLOCKMHZ: response,
            }
        }
    ),
    OpenThermReport.TEMP_SENSOR_FUNCTION: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_TEMP_SENSOR: OpenThermTemperatureSensorFunction(response),
            }
        }
    ),
    OpenThermReport.GPIO_MODES: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_GPIO_A: OpenThermGPIOMode(int(response[0])),
                v.OTGW_GPIO_B: OpenThermGPIOMode(int(response[1])),
            },
        }
    ),
    OpenThermReport.GPIO_STATES: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_GPIO_A_STATE: int(response[0]),
                v.OTGW_GPIO_B_STATE: int(response[1]),
            }
        }
    ),
    OpenThermReport.LED_MODES: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_LED_A: OpenThermLEDMode(response[0]),
                v.OTGW_LED_B: OpenThermLEDMode(response[1]),
                v.OTGW_LED_C: OpenThermLEDMode(response[2]),
                v.OTGW_LED_D: OpenThermLEDMode(response[3]),
                v.OTGW_LED_E: OpenThermLEDMode(response[4]),
                v.OTGW_LED_F: OpenThermLEDMode(response[5]),
            },
        }
    ),
    OpenThermReport.OP_MODE: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_MODE: OpenThermGatewayOpMode(response),
            },
        }
    ),
    OpenThermReport.SETPOINT_OVERRIDE: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_SETP_OVRD_MODE: OpenThermSetpointOverrideMode(
                    response[0].upper()
                ),
            },
            OpenThermDataSource.THERMOSTAT: {
                v.DATA_ROOM_SETPOINT_OVRD: None
                if response[0].upper() == OpenThermSetpointOverrideMode.NOT_ACTIVE
                else float(response[1:]),
            },
        }
    ),
    OpenThermReport.SMART_PWR_MODE: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_SMART_PWR: OpenThermSmartPowerMode(response.lower()),
            },
        }
    ),
    OpenThermReport.RESET_CAUSE: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_RST_CAUSE: OpenThermResetCause(response),
            },
        }
    ),
    OpenThermReport.THERMOSTAT_DETECTION_STATE: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_THRM_DETECT: OpenThermThermostatDetection(response),
            },
        }
    ),
    OpenThermReport.SETBACK_TEMPERATURE: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_SB_TEMP: float(response),
            },
        }
    ),
    OpenThermReport.TWEAKS: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_IGNORE_TRANSITIONS: int(response[0]),
                v.OTGW_OVRD_HB: int(response[1]),
            },
        }
    ),
    OpenThermReport.VREF: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_VREF: OpenThermVoltageReferenceLevel(int(response)),
            },
        }
    ),
    OpenThermReport.DHW: (
        lambda response: {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_DHW_OVRD: response,
            },
        }
    ),
}


def convert_report_response_to_status_update(
    report_type: OpenThermReport, response: str
) -> dict[OpenThermDataSource, dict] | None:
    """Convert a report response to a status update dict."""
    if report_type not in _CONVERSIONS:
        return
    try:
        return _CONVERSIONS[report_type](response[2:])
    except ValueError:
        return
