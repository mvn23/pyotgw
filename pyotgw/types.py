"""pyotgw types."""

from enum import Enum, IntEnum, StrEnum


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


class OpenThermGatewayOpMode(StrEnum):
    """OpenTherm Gateway operating modes."""

    GATEWAY = "G"
    MONITOR = "M"


class OpenThermGPIOMode(IntEnum):
    """OpenTherm Gateway GPIO modes."""

    INPUT = 0
    GROUND = 1
    VCC = 2
    LED_E = 3
    LED_F = 4
    HOME = 5
    AWAY = 6
    DS1820 = 7
    DHW_BLOCK = 8


class OpenThermHotWaterOverrideMode(StrEnum):
    """Hot water override modes."""

    FORCE_OFF = "0"
    FORCE_ON = "1"
    THERMOSTAT_CONTROLLED = "A"


class OpenThermLEDMode(StrEnum):
    """OpenTherm Gateway LED modes."""

    RX_ANY = "R"
    TX_ANY = "X"
    THERMOSTAT_TRAFFIC = "T"
    BOILER_TRAFFIC = "B"
    SETPOINT_OVERRIDE_ACTIVE = "O"
    FLAME_ON = "F"
    CENTRAL_HEATING_ON = "H"
    HOT_WATER_ON = "W"
    COMFORT_MODE_ON = "C"
    TX_ERROR_DETECTED = "E"
    BOILER_MAINTENANCE_REQUIRED = "M"
    RAISED_POWER_MODE_ACTIVE = "P"


class OpenThermMessageID(Enum):
    """OpenTherm message IDs."""

    STATUS = b"\x00"
    TSET = b"\x01"
    MCONFIG = b"\x02"
    SCONFIG = b"\x03"
    COMMAND = b"\x04"
    ASFFLAGS = b"\x05"
    RBPFLAGS = b"\x06"
    COOLING = b"\x07"
    TSETC2 = b"\x08"
    TROVRD = b"\x09"
    TSP = b"\x0a"
    TSPIDX = b"\x0b"
    FHBSIZE = b"\x0c"
    FHBIDX = b"\x0d"
    MAXRMOD = b"\x0e"
    MAXCAPMINMOD = b"\x0f"
    TRSET = b"\x10"
    RELMOD = b"\x11"
    CHPRESS = b"\x12"
    DHWFLOW = b"\x13"
    TIME = b"\x14"
    DATE = b"\x15"
    YEAR = b"\x16"
    TRSET2 = b"\x17"
    TROOM = b"\x18"
    TBOILER = b"\x19"
    TDHW = b"\x1a"
    TOUTSIDE = b"\x1b"
    TRET = b"\x1c"
    TSTOR = b"\x1d"
    TCOLL = b"\x1e"
    TFLOWCH2 = b"\x1f"
    TDHW2 = b"\x20"
    TEXHAUST = b"\x21"
    TDHWSETUL = b"\x30"
    TCHSETUL = b"\x31"
    OTCCURVEUL = b"\x32"
    TDHWSET = b"\x38"
    MAXTSET = b"\x39"
    OTCCURVE = b"\x3a"
    STATUSVH = b"\x46"
    RELVENTPOS = b"\x47"
    RELVENT = b"\x4d"
    ROVRD = b"\x64"
    OEMDIAG = b"\x73"
    BURNSTARTS = b"\x74"
    CHPUMPSTARTS = b"\x75"
    DHWPUMPSTARTS = b"\x76"
    DHWBURNSTARTS = b"\x77"
    BURNHRS = b"\x78"
    CHPUMPHRS = b"\x79"
    DHWPUMPHRS = b"\x7a"
    DHWBURNHRS = b"\x7b"
    OTVERM = b"\x7c"
    OTVERS = b"\x7d"
    MVER = b"\x7e"
    SVER = b"\x7f"

    def __int__(self) -> int:
        """Return value as int."""
        return int.from_bytes(self.value, "big")


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


class OpenThermReport(StrEnum):
    """OpenTherm reports."""

    ABOUT = "A"
    BUILD = "B"
    CLOCK_SPEED = "C"
    TEMP_SENSOR_FUNCTION = "D"
    GPIO_MODES = "G"
    GPIO_STATES = "I"
    LED_MODES = "L"
    OP_MODE = "M"
    SETPOINT_OVERRIDE = "O"
    SMART_PWR_MODE = "P"
    RESET_CAUSE = "Q"
    THERMOSTAT_DETECTION_STATE = "R"
    SETBACK_TEMPERATURE = "S"
    TWEAKS = "T"
    VREF = "V"
    DHW = "W"


class OpenThermResetCause(StrEnum):
    """Gateway reset causes."""

    BROWNOUT = "B"
    SERIAL_COMMAND = "C"
    RESET_BUTTON = "E"
    STUCK_IN_LOOP = "L"
    STACK_OVERFLOW = "O"
    POWER_ON = "P"
    SERIAL_BREAK = "S"
    STACK_UNDERFLOW = "U"
    WATCHDOG = "W"


class OpenThermSetpointOverrideMode(StrEnum):
    """Setpoint override modes."""

    CONSTANT = "C"
    NOT_ACTIVE = "N"
    TEMPORARY = "T"


class OpenThermSmartPowerMode(StrEnum):
    """Smart power modes."""

    LOW = "low power"
    MEDIUM = "medium power"
    HIGH = "high power"


class OpenThermTemperatureSensorFunction(StrEnum):
    """Temperature sensor functions."""

    OUTSIDE_TEMPERATURE = "O"
    RETURN_WATER_TEMPERATURE = "R"


class OpenThermThermostatDetection(StrEnum):
    """Thermostat detection modes."""

    AUTO_DETECT = "D"
    CELCIA_20 = "C"
    ISENSE = "I"
    STANDARD = "S"


class OpenThermVoltageReferenceLevel(IntEnum):
    """Voltage reference levels."""

    LEVEL_0 = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4
    LEVEL_5 = 5
    LEVEL_6 = 6
    LEVEL_7 = 7
    LEVEL_8 = 8
    LEVEL_9 = 9
