"""Global pyotgw values"""

from .types import OpenThermDataSource

DEFAULT_STATUS = {
    OpenThermDataSource.BOILER: {},
    OpenThermDataSource.GATEWAY: {},
    OpenThermDataSource.THERMOSTAT: {},
}

# MSG_STATUS
DATA_MASTER_CH_ENABLED = "master_ch_enabled"
DATA_MASTER_DHW_ENABLED = "master_dhw_enabled"
DATA_MASTER_COOLING_ENABLED = "master_cooling_enabled"
DATA_MASTER_OTC_ENABLED = "master_otc_enabled"
DATA_MASTER_CH2_ENABLED = "master_ch2_enabled"
DATA_SLAVE_FAULT_IND = "slave_fault_indication"
DATA_SLAVE_CH_ACTIVE = "slave_ch_active"
DATA_SLAVE_DHW_ACTIVE = "slave_dhw_active"
DATA_SLAVE_FLAME_ON = "slave_flame_on"
DATA_SLAVE_COOLING_ACTIVE = "slave_cooling_active"
DATA_SLAVE_CH2_ACTIVE = "slave_ch2_active"
DATA_SLAVE_DIAG_IND = "slave_diagnostic_indication"

# MSG_TSET
DATA_CONTROL_SETPOINT = "control_setpoint"

# MSG_MCONFIG
DATA_MASTER_MEMBERID = "master_memberid"

# MSG_SCONFIG
DATA_SLAVE_DHW_PRESENT = "slave_dhw_present"
DATA_SLAVE_CONTROL_TYPE = "slave_control_type"
DATA_SLAVE_COOLING_SUPPORTED = "slave_cooling_supported"
DATA_SLAVE_DHW_CONFIG = "slave_dhw_config"
DATA_SLAVE_MASTER_LOW_OFF_PUMP = "slave_master_low_off_pump"
DATA_SLAVE_CH2_PRESENT = "slave_ch2_present"
DATA_SLAVE_MEMBERID = "slave_memberid"

# MSG_COMMAND

# MSG_ASFFLAGS
DATA_SLAVE_SERVICE_REQ = "slave_service_required"
DATA_SLAVE_REMOTE_RESET = "slave_remote_reset"
DATA_SLAVE_LOW_WATER_PRESS = "slave_low_water_pressure"
DATA_SLAVE_GAS_FAULT = "slave_gas_fault"
DATA_SLAVE_AIR_PRESS_FAULT = "slave_air_pressure_fault"
DATA_SLAVE_WATER_OVERTEMP = "slave_water_overtemp"
DATA_SLAVE_OEM_FAULT = "slave_oem_fault"

# MSG_RBPFLAGS
DATA_REMOTE_TRANSFER_DHW = "remote_transfer_dhw"
DATA_REMOTE_TRANSFER_MAX_CH = "remote_transfer_max_ch"
DATA_REMOTE_RW_DHW = "remote_rw_dhw"
DATA_REMOTE_RW_MAX_CH = "remote_rw_max_ch"

# MSG_COOLING
DATA_COOLING_CONTROL = "cooling_control"

# MSG_TSETC2
DATA_CONTROL_SETPOINT_2 = "control_setpoint_2"

# MSG_TROVRD
DATA_ROOM_SETPOINT_OVRD = "room_setpoint_ovrd"

# MSG_TSP

# MSG_TSPIDX

# MSG_FHBSIZE

# MSG_FHBIDX

# MSG_MAXRMOD
DATA_SLAVE_MAX_RELATIVE_MOD = "slave_max_relative_modulation"

# MSG_MAXCAPMINMOD
DATA_SLAVE_MAX_CAPACITY = "slave_max_capacity"
DATA_SLAVE_MIN_MOD_LEVEL = "slave_min_mod_level"

# MSG_TRSET
DATA_ROOM_SETPOINT = "room_setpoint"

# MSG_RELMOD
DATA_REL_MOD_LEVEL = "relative_mod_level"

# MSG_CHPRESS
DATA_CH_WATER_PRESS = "ch_water_pressure"

# MSG_DHWFLOW
DATA_DHW_FLOW_RATE = "dhw_flow_rate"

# MSG_TIME

# MSG_DATE

# MSG_YEAR

# MSG_TRSET2
DATA_ROOM_SETPOINT_2 = "room_setpoint_2"

# MSG_TROOM
DATA_ROOM_TEMP = "room_temp"

# MSG_TBOILER
DATA_CH_WATER_TEMP = "ch_water_temp"

# MSG_TDHW
DATA_DHW_TEMP = "dhw_temp"

# MSG_TOUTSIDE
DATA_OUTSIDE_TEMP = "outside_temp"

# MSG_TRET
DATA_RETURN_WATER_TEMP = "return_water_temp"

# MSG_TSTOR
DATA_SOLAR_STORAGE_TEMP = "solar_storage_temp"

# MSG_TCOLL
DATA_SOLAR_COLL_TEMP = "solar_coll_temp"

# MSG_TFLOWCH2
DATA_CH_WATER_TEMP_2 = "ch_water_temp_2"

# MSG_TDHW2
DATA_DHW_TEMP_2 = "dhw_temp_2"

# MSG_TEXHAUST
DATA_EXHAUST_TEMP = "exhaust_temp"

# MSG_TDHWSETUL
DATA_SLAVE_DHW_MAX_SETP = "slave_dhw_max_setp"
DATA_SLAVE_DHW_MIN_SETP = "slave_dhw_min_setp"

# MSG_TCHSETUL
DATA_SLAVE_CH_MAX_SETP = "slave_ch_max_setp"
DATA_SLAVE_CH_MIN_SETP = "slave_ch_min_setp"

# MSG_OTCCURVEUL

# MSG_TDHWSET
DATA_DHW_SETPOINT = "dhw_setpoint"

# MSG_MAXTSET
DATA_MAX_CH_SETPOINT = "max_ch_setpoint"

# MSG_OTCCURVE

# MSG_STATUSVH
DATA_VH_MASTER_VENT_ENABLED = "vh_master_vent_enabled"
DATA_VH_MASTER_BYPASS_POS = "vh_master_bypass_pos"
DATA_VH_MASTER_BYPASS_MODE = "vh_master_bypass_mode"
DATA_VH_MASTER_FREE_VENT_MODE = "vh_master_free_vent_mode"
DATA_VH_SLAVE_FAULT_INDICATE = "vh_slave_fault_indicate"
DATA_VH_SLAVE_VENT_MODE = "vh_slave_vent_mode"
DATA_VH_SLAVE_BYPASS_STATUS = "vh_slave_bypass_status"
DATA_VH_SLAVE_BYPASS_AUTO_STATUS = "vh_slave_bypass_auto_status"
DATA_VH_SLAVE_FREE_VENT_STATUS = "vh_slave_free_vent_status"
DATA_VH_SLAVE_DIAG_INDICATE = "vh_slave_diag_indicate"

# MSG_RELVENTPOS
DATA_VH_CONTROL_SETPOINT = "vh_control_setpoint"

# MSG_RELVENT
DATA_VH_RELATIVE_VENT = "vh_relative_vent"

# MSG_ROVRD
DATA_ROVRD_MAN_PRIO = "rovrd_man_prio"
DATA_ROVRD_AUTO_PRIO = "rovrd_auto_prio"

# MSG_OEMDIAG
DATA_OEM_DIAG = "oem_diag"

# MSG_BURNSTARTS
DATA_TOTAL_BURNER_STARTS = "burner_starts"

# MSG_CHPUMPSTARTS
DATA_CH_PUMP_STARTS = "ch_pump_starts"

# MSG_DHWPUMPSTARTS
DATA_DHW_PUMP_STARTS = "dhw_pump_starts"

# MSG_DHWBURNSTARTS
DATA_DHW_BURNER_STARTS = "dhw_burner_starts"

# MSG_BURNHRS
DATA_TOTAL_BURNER_HOURS = "burner_hours"

# MSG_CHPUMPHRS
DATA_CH_PUMP_HOURS = "ch_pump_hours"

# MSG_DHWPUMPHRS
DATA_DHW_PUMP_HOURS = "dhw_pump_hours"

# MSG_DHWBURNHRS
DATA_DHW_BURNER_HOURS = "dhw_burner_hours"

# MSG_OTVERM
DATA_MASTER_OT_VERSION = "master_ot_version"

# MSG_OTVERS
DATA_SLAVE_OT_VERSION = "slave_ot_version"

# MSG_MVER
DATA_MASTER_PRODUCT_TYPE = "master_product_type"
DATA_MASTER_PRODUCT_VERSION = "master_product_version"

# MSG_SVER
DATA_SLAVE_PRODUCT_TYPE = "slave_product_type"
DATA_SLAVE_PRODUCT_VERSION = "slave_product_version"

OTGW_DEFAULT_TIMEOUT = 3

OTGW_MODE = "otgw_mode"
OTGW_DHW_OVRD = "otgw_dhw_ovrd"
OTGW_ABOUT = "otgw_about"
OTGW_BUILD = "otgw_build"
OTGW_CLOCKMHZ = "otgw_clockmhz"
OTGW_LED_A = "otgw_led_a"
OTGW_LED_B = "otgw_led_b"
OTGW_LED_C = "otgw_led_c"
OTGW_LED_D = "otgw_led_d"
OTGW_LED_E = "otgw_led_e"
OTGW_LED_F = "otgw_led_f"
OTGW_GPIO_A = "otgw_gpio_a"
OTGW_GPIO_B = "otgw_gpio_b"
OTGW_GPIO_A_STATE = "otgw_gpio_a_state"
OTGW_GPIO_B_STATE = "otgw_gpio_b_state"
OTGW_RST_CAUSE = "otgw_reset_cause"
OTGW_SB_TEMP = "otgw_setback_temp"
OTGW_SETP_OVRD_MODE = "otgw_setpoint_ovrd_mode"
OTGW_SMART_PWR = "otgw_smart_pwr"
OTGW_TEMP_SENSOR = "otgw_temp_sensor"
OTGW_THRM_DETECT = "otgw_thermostat_detect"
OTGW_IGNORE_TRANSITIONS = "otgw_ignore_transitions"
OTGW_OVRD_HB = "otgw_ovrd_high_byte"
OTGW_VREF = "otgw_vref"

OTGW_SETP_OVRD_TEMPORARY = "T"
OTGW_SETP_OVRD_PERMANENT = "C"
OTGW_SETP_OVRD_DISABLED = "N"

OTGW_REPORT_ABOUT = "A"
OTGW_REPORT_BUILDDATE = "B"
OTGW_REPORT_CLOCKMHZ = "C"
OTGW_REPORT_TEMP_SENSOR = "D"
OTGW_REPORT_GPIO_FUNCS = "G"
OTGW_REPORT_GPIO_STATES = "I"
OTGW_REPORT_LED_FUNCS = "L"
OTGW_REPORT_GW_MODE = "M"
OTGW_REPORT_SETPOINT_OVRD = "O"
OTGW_REPORT_SMART_PWR = "P"
OTGW_REPORT_RST_CAUSE = "Q"
OTGW_REPORT_THERMOSTAT_DETECT = "R"
OTGW_REPORT_SETBACK_TEMP = "S"
OTGW_REPORT_TWEAKS = "T"
OTGW_REPORT_VREF = "V"
OTGW_REPORT_DHW_SETTING = "W"

OTGW_REPORTS = {
    OTGW_REPORT_ABOUT: OTGW_ABOUT,
    OTGW_REPORT_BUILDDATE: OTGW_BUILD,
    OTGW_REPORT_CLOCKMHZ: OTGW_CLOCKMHZ,
    OTGW_REPORT_DHW_SETTING: OTGW_DHW_OVRD,
    OTGW_REPORT_GPIO_FUNCS: [OTGW_GPIO_A, OTGW_GPIO_B],
    OTGW_REPORT_GPIO_STATES: [OTGW_GPIO_A_STATE, OTGW_GPIO_B_STATE],
    OTGW_REPORT_LED_FUNCS: [
        OTGW_LED_A,
        OTGW_LED_B,
        OTGW_LED_C,
        OTGW_LED_D,
        OTGW_LED_E,
        OTGW_LED_F,
    ],
    OTGW_REPORT_GW_MODE: OTGW_MODE,
    OTGW_REPORT_RST_CAUSE: OTGW_RST_CAUSE,
    OTGW_REPORT_SETBACK_TEMP: OTGW_SB_TEMP,
    OTGW_REPORT_SETPOINT_OVRD: OTGW_SETP_OVRD_MODE,
    OTGW_REPORT_SMART_PWR: OTGW_SMART_PWR,
    OTGW_REPORT_TEMP_SENSOR: OTGW_TEMP_SENSOR,
    OTGW_REPORT_THERMOSTAT_DETECT: OTGW_THRM_DETECT,
    OTGW_REPORT_TWEAKS: [OTGW_IGNORE_TRANSITIONS, OTGW_OVRD_HB],
    OTGW_REPORT_VREF: OTGW_VREF,
}

NO_GOOD = "NG"
SYNTAX_ERR = "SE"
BAD_VALUE = "BV"
OUT_OF_RANGE = "OR"
NO_SPACE = "NS"
NOT_FOUND = "NF"
OVERRUN_ERR = "OE"
MPC_ERR = "MPC"

OTGW_ERRS = {
    NO_GOOD: RuntimeError(
        "No Good: The command code is unknown or unsupported on this "
        "version of the OpenTherm Gateway."
    ),
    SYNTAX_ERR: SyntaxError(
        "Syntax Error: The command contained an "
        "unexpected character or was incomplete."
    ),
    BAD_VALUE: ValueError(
        "Bad Value: The command contained a data value that is not allowed or not "
        "supported on this version of the OpenTherm Gateway."
    ),
    OUT_OF_RANGE: RuntimeError(
        "Out of Range: A number was specified outside of the allowed range."
    ),
    NO_SPACE: RuntimeError(
        "No Space: The alternative Data-ID could not be "
        "added because the table is full."
    ),
    NOT_FOUND: RuntimeError(
        "Not Found: The specified alternative Data-ID "
        "could not be removed because it does not exist "
        "in the table."
    ),
    OVERRUN_ERR: RuntimeError(
        "Overrun Error: The processor was busy and "
        "failed to process all received characters."
    ),
    MPC_ERR: RuntimeError("MPC Error"),
}
