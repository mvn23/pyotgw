"""pyotgw types."""

from enum import IntEnum, StrEnum


class OpenThermCommand(StrEnum):
    """OpenTherm commands."""

    TARGET_TEMP = "TT"
    TARGET_TEMP_CONST = "TC"
    OUTSIDE_TEMP = "OT"
    SET_CLOCK = "SC"
    HOT_WATER = "HW"
    REPORT = "PR"
    SUMMARY = "PS"
    MODE = "GW"
    LED_A = "LA"
    LED_B = "LB"
    LED_C = "LC"
    LED_D = "LD"
    LED_E = "LE"
    LED_F = "LF"
    GPIO_A = "GA"
    GPIO_B = "GB"
    SETBACK = "SB"
    TEMP_SENSOR = "TS"
    ADD_ALT = "AA"
    DEL_ALT = "DA"
    UNKNOWN_ID = "UI"
    KNOWN_ID = "KI"
    PRIO_MSG = "PM"
    SET_RESP = "SR"
    CLR_RESP = "CR"
    SET_MAX = "SH"
    SET_WATER = "SW"
    MAX_MOD = "MM"
    CONTROL_SETPOINT = "CS"
    CONTROL_SETPOINT_2 = "C2"
    CONTROL_HEATING = "CH"
    CONTROL_HEATING_2 = "H2"
    VENT = "VS"
    RST_CNT = "RS"
    IGNORE_TRANS = "IT"
    OVRD_HIGH = "OH"
    OVRD_THRMST = "FT"
    VREF = "VR"


class OpenThermDataSource(StrEnum):
    """OpenTherm data sources."""

    BOILER = "boiler"
    GATEWAY = "gateway"
    THERMOSTAT = "thermostat"


class OpenThermMessageType(IntEnum):
    """OpenTherm message types."""

    READ_DATA = 0
    WRITE_DATA = 1
    INVALID_DATA = 2
    RESERVED = 3
    READ_ACK = 4
    WRITE_ACK = 5
    DATA_INVALID = 6
    UNKNOWN_DATAID = 7
