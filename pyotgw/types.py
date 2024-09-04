"""pyotgw types."""

from enum import IntEnum, StrEnum


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
