"""Test data for pyotgw tests"""

from types import SimpleNamespace

import pyotgw.vars as v

_report_responses_51 = {
    v.OTGW_REPORT_ABOUT: "A=OpenTherm Gateway 5.1",
    v.OTGW_REPORT_BUILDDATE: "B=17:44 11-02-2021",
    v.OTGW_REPORT_CLOCKMHZ: "C=4 MHz",
    v.OTGW_REPORT_DHW_SETTING: "W=A",
    v.OTGW_REPORT_GPIO_FUNCS: "G=10",
    v.OTGW_REPORT_GPIO_STATES: "I=00",
    v.OTGW_REPORT_LED_FUNCS: "L=FXOMPC",
    v.OTGW_REPORT_GW_MODE: "M=G",
    v.OTGW_REPORT_RST_CAUSE: "Q=C",
    v.OTGW_REPORT_SETBACK_TEMP: "S=16.50",
    v.OTGW_REPORT_SETPOINT_OVRD: "O=T20.50",
    v.OTGW_REPORT_SMART_PWR: "P=Low power",
    v.OTGW_REPORT_TEMP_SENSOR: "D=0",
    v.OTGW_REPORT_THERMOSTAT_DETECT: "R=D",
    v.OTGW_REPORT_TWEAKS: "T=11",
    v.OTGW_REPORT_VREF: "V=3",
}

_report_responses_42 = {
    v.OTGW_REPORT_ABOUT: "A=OpenTherm Gateway 4.2.5",
    v.OTGW_REPORT_BUILDDATE: "B=17:59 20-10-2015",
    v.OTGW_REPORT_CLOCKMHZ: None,
    v.OTGW_REPORT_DHW_SETTING: "W=A",
    v.OTGW_REPORT_GPIO_FUNCS: "G=10",
    v.OTGW_REPORT_GPIO_STATES: "I=00",
    v.OTGW_REPORT_LED_FUNCS: "L=FXOMPC",
    v.OTGW_REPORT_GW_MODE: "M=G",
    v.OTGW_REPORT_RST_CAUSE: "Q=C",
    v.OTGW_REPORT_SETBACK_TEMP: "S=16.50",
    v.OTGW_REPORT_SETPOINT_OVRD: "O=T20.50",
    v.OTGW_REPORT_SMART_PWR: "P=Low power",
    v.OTGW_REPORT_THERMOSTAT_DETECT: "R=D",
    v.OTGW_REPORT_TWEAKS: "T=11",
    v.OTGW_REPORT_VREF: "V=3",
}

_report_expect_51 = {
    v.BOILER: {},
    v.OTGW: {
        v.OTGW_ABOUT: "OpenTherm Gateway 5.1",
        v.OTGW_BUILD: "17:44 11-02-2021",
        v.OTGW_CLOCKMHZ: "4 MHz",
        v.OTGW_DHW_OVRD: "A",
        v.OTGW_MODE: "G",
        v.OTGW_RST_CAUSE: "C",
        v.OTGW_SMART_PWR: "Low power",
        v.OTGW_TEMP_SENSOR: "0",
        v.OTGW_THRM_DETECT: "D",
        v.OTGW_SETP_OVRD_MODE: "T",
        v.OTGW_GPIO_A: 1,
        v.OTGW_GPIO_B: 0,
        v.OTGW_LED_A: "F",
        v.OTGW_LED_B: "X",
        v.OTGW_LED_C: "O",
        v.OTGW_LED_D: "M",
        v.OTGW_LED_E: "P",
        v.OTGW_LED_F: "C",
        v.OTGW_IGNORE_TRANSITIONS: 1,
        v.OTGW_OVRD_HB: 1,
        v.OTGW_SB_TEMP: 16.5,
        v.OTGW_VREF: 3,
    },
    v.THERMOSTAT: {v.DATA_ROOM_SETPOINT_OVRD: 20.5},
}

_report_expect_42 = {
    v.BOILER: {},
    v.OTGW: {
        v.OTGW_ABOUT: "OpenTherm Gateway 4.2.5",
        v.OTGW_BUILD: "17:59 20-10-2015",
        v.OTGW_CLOCKMHZ: None,
        v.OTGW_DHW_OVRD: "A",
        v.OTGW_MODE: "G",
        v.OTGW_RST_CAUSE: "C",
        v.OTGW_SMART_PWR: "Low power",
        v.OTGW_TEMP_SENSOR: None,
        v.OTGW_THRM_DETECT: "D",
        v.OTGW_SETP_OVRD_MODE: "T",
        v.OTGW_GPIO_A: 1,
        v.OTGW_GPIO_B: 0,
        v.OTGW_LED_A: "F",
        v.OTGW_LED_B: "X",
        v.OTGW_LED_C: "O",
        v.OTGW_LED_D: "M",
        v.OTGW_LED_E: "P",
        v.OTGW_LED_F: "C",
        v.OTGW_IGNORE_TRANSITIONS: 1,
        v.OTGW_OVRD_HB: 1,
        v.OTGW_SB_TEMP: 16.5,
        v.OTGW_VREF: 3,
    },
    v.THERMOSTAT: {v.DATA_ROOM_SETPOINT_OVRD: 20.5},
}

pygw_reports = SimpleNamespace(
    expect_42=_report_expect_42,
    expect_51=_report_expect_51,
    report_responses_42=_report_responses_42,
    report_responses_51=_report_responses_51,
)


_status_5 = (
    "10101010/01010101,1.23,01010101/10101010,2.34,3.45,4.56,1/0,5.67,6.78,7.89,8.90,"
    "9.09,0.98,9.87,8.76,7.65,6.54,5.43,2,34/56,78/90,4.32,3.21,10101010/01010101,9,8,"
    "7654,6543,54321,43210,32101,21012,10123,99"
)
_status_expect_5 = {
    v.BOILER: {
        v.DATA_SLAVE_FAULT_IND: 1,
        v.DATA_SLAVE_CH_ACTIVE: 0,
        v.DATA_SLAVE_DHW_ACTIVE: 1,
        v.DATA_SLAVE_FLAME_ON: 0,
        v.DATA_SLAVE_COOLING_ACTIVE: 1,
        v.DATA_SLAVE_CH2_ACTIVE: 0,
        v.DATA_SLAVE_DIAG_IND: 1,
        v.DATA_REMOTE_TRANSFER_DHW: 1,
        v.DATA_REMOTE_TRANSFER_MAX_CH: 0,
        v.DATA_REMOTE_RW_DHW: 0,
        v.DATA_REMOTE_RW_MAX_CH: 1,
        v.DATA_SLAVE_MAX_RELATIVE_MOD: 4.56,
        v.DATA_SLAVE_MAX_CAPACITY: 1,
        v.DATA_SLAVE_MIN_MOD_LEVEL: 0,
        v.DATA_REL_MOD_LEVEL: 6.78,
        v.DATA_CH_WATER_PRESS: 7.89,
        v.DATA_DHW_FLOW_RATE: 8.90,
        v.DATA_CH_WATER_TEMP: 9.87,
        v.DATA_DHW_TEMP: 8.76,
        v.DATA_OUTSIDE_TEMP: 7.65,
        v.DATA_RETURN_WATER_TEMP: 6.54,
        v.DATA_CH_WATER_TEMP_2: 5.43,
        v.DATA_EXHAUST_TEMP: 2,
        v.DATA_SLAVE_DHW_MAX_SETP: 34,
        v.DATA_SLAVE_DHW_MIN_SETP: 56,
        v.DATA_SLAVE_CH_MAX_SETP: 78,
        v.DATA_SLAVE_CH_MIN_SETP: 90,
        v.DATA_DHW_SETPOINT: 4.32,
        v.DATA_MAX_CH_SETPOINT: 3.21,
        v.DATA_VH_SLAVE_FAULT_INDICATE: 1,
        v.DATA_VH_SLAVE_VENT_MODE: 0,
        v.DATA_VH_SLAVE_BYPASS_STATUS: 1,
        v.DATA_VH_SLAVE_BYPASS_AUTO_STATUS: 0,
        v.DATA_VH_SLAVE_FREE_VENT_STATUS: 1,
        v.DATA_VH_SLAVE_DIAG_INDICATE: 1,
        v.DATA_VH_RELATIVE_VENT: 8,
        v.DATA_TOTAL_BURNER_STARTS: 7654,
        v.DATA_CH_PUMP_STARTS: 6543,
        v.DATA_DHW_PUMP_STARTS: 54321,
        v.DATA_DHW_BURNER_STARTS: 43210,
        v.DATA_TOTAL_BURNER_HOURS: 32101,
        v.DATA_CH_PUMP_HOURS: 21012,
        v.DATA_DHW_PUMP_HOURS: 10123,
        v.DATA_DHW_BURNER_HOURS: 99,
    },
    v.OTGW: {},
    v.THERMOSTAT: {
        v.DATA_MASTER_CH_ENABLED: 0,
        v.DATA_MASTER_DHW_ENABLED: 1,
        v.DATA_MASTER_COOLING_ENABLED: 0,
        v.DATA_MASTER_OTC_ENABLED: 1,
        v.DATA_MASTER_CH2_ENABLED: 0,
        v.DATA_CONTROL_SETPOINT: 1.23,
        v.DATA_ROOM_SETPOINT: 5.67,
        v.DATA_COOLING_CONTROL: 2.34,
        v.DATA_CONTROL_SETPOINT_2: 3.45,
        v.DATA_ROOM_SETPOINT_2: 9.09,
        v.DATA_ROOM_TEMP: 0.98,
        v.DATA_VH_MASTER_VENT_ENABLED: 0,
        v.DATA_VH_MASTER_BYPASS_POS: 1,
        v.DATA_VH_MASTER_BYPASS_MODE: 0,
        v.DATA_VH_MASTER_FREE_VENT_MODE: 1,
        v.DATA_VH_CONTROL_SETPOINT: 9,
    },
}

_status_4 = (
    "10101010/01010101,1.23,01010101/10101010,2.34,0/1,3.45,4.56,5.67,6.78,7.89,8.90,"
    "9.09,0.98,12/34,56/78,9.87,8.76,1234,2345,3456,4567,5678,6789,7890,8909"
)
_status_expect_4 = {
    v.BOILER: {
        v.DATA_SLAVE_FAULT_IND: 1,
        v.DATA_SLAVE_CH_ACTIVE: 0,
        v.DATA_SLAVE_DHW_ACTIVE: 1,
        v.DATA_SLAVE_FLAME_ON: 0,
        v.DATA_SLAVE_COOLING_ACTIVE: 1,
        v.DATA_SLAVE_CH2_ACTIVE: 0,
        v.DATA_SLAVE_DIAG_IND: 1,
        v.DATA_REMOTE_TRANSFER_DHW: 1,
        v.DATA_REMOTE_TRANSFER_MAX_CH: 0,
        v.DATA_REMOTE_RW_DHW: 0,
        v.DATA_REMOTE_RW_MAX_CH: 1,
        v.DATA_SLAVE_MAX_RELATIVE_MOD: 2.34,
        v.DATA_SLAVE_MAX_CAPACITY: 0,
        v.DATA_SLAVE_MIN_MOD_LEVEL: 1,
        v.DATA_REL_MOD_LEVEL: 4.56,
        v.DATA_CH_WATER_PRESS: 5.67,
        v.DATA_CH_WATER_TEMP: 7.89,
        v.DATA_DHW_TEMP: 8.90,
        v.DATA_OUTSIDE_TEMP: 9.09,
        v.DATA_RETURN_WATER_TEMP: 0.98,
        v.DATA_SLAVE_DHW_MAX_SETP: 12,
        v.DATA_SLAVE_DHW_MIN_SETP: 34,
        v.DATA_SLAVE_CH_MAX_SETP: 56,
        v.DATA_SLAVE_CH_MIN_SETP: 78,
        v.DATA_DHW_SETPOINT: 9.87,
        v.DATA_MAX_CH_SETPOINT: 8.76,
        v.DATA_TOTAL_BURNER_STARTS: 1234,
        v.DATA_CH_PUMP_STARTS: 2345,
        v.DATA_DHW_PUMP_STARTS: 3456,
        v.DATA_DHW_BURNER_STARTS: 4567,
        v.DATA_TOTAL_BURNER_HOURS: 5678,
        v.DATA_CH_PUMP_HOURS: 6789,
        v.DATA_DHW_PUMP_HOURS: 7890,
        v.DATA_DHW_BURNER_HOURS: 8909,
    },
    v.OTGW: {},
    v.THERMOSTAT: {
        v.DATA_MASTER_CH_ENABLED: 0,
        v.DATA_MASTER_DHW_ENABLED: 1,
        v.DATA_MASTER_COOLING_ENABLED: 0,
        v.DATA_MASTER_OTC_ENABLED: 1,
        v.DATA_MASTER_CH2_ENABLED: 0,
        v.DATA_CONTROL_SETPOINT: 1.23,
        v.DATA_ROOM_SETPOINT: 3.45,
        v.DATA_ROOM_TEMP: 6.78,
    },
}

pygw_status = SimpleNamespace(
    expect_4=_status_expect_4,
    expect_5=_status_expect_5,
    status_4=_status_4,
    status_5=_status_5,
)


pygw_proto_messages = (
    # Invalid message ID
    (
        ("A", 114, None, None, None),
        None,
    ),
    # _get_flag8
    (
        ("T", v.READ_DATA, v.MSG_STATUS, b"\x43", b"\x00"),
        {
            v.BOILER: {},
            v.OTGW: {},
            v.THERMOSTAT: {
                v.DATA_MASTER_CH_ENABLED: 1,
                v.DATA_MASTER_DHW_ENABLED: 1,
                v.DATA_MASTER_COOLING_ENABLED: 0,
                v.DATA_MASTER_OTC_ENABLED: 0,
                v.DATA_MASTER_CH2_ENABLED: 0,
            },
        },
    ),
    # _get_f8_8
    (
        ("B", v.WRITE_ACK, v.MSG_TDHWSET, b"\x14", b"\x80"),
        {v.BOILER: {v.DATA_DHW_SETPOINT: 20.5}, v.OTGW: {}, v.THERMOSTAT: {}},
    ),
    # _get_flag8 with skipped bits
    (
        (
            "R",
            v.READ_ACK,
            v.MSG_STATUSVH,
            b"\00",
            int("01010101", 2).to_bytes(1, "big"),
        ),
        {
            v.BOILER: {
                v.DATA_VH_SLAVE_FAULT_INDICATE: 1,
                v.DATA_VH_SLAVE_VENT_MODE: 0,
                v.DATA_VH_SLAVE_BYPASS_STATUS: 1,
                v.DATA_VH_SLAVE_BYPASS_AUTO_STATUS: 0,
                v.DATA_VH_SLAVE_FREE_VENT_STATUS: 1,
                v.DATA_VH_SLAVE_DIAG_INDICATE: 1,
            },
            v.OTGW: {},
            v.THERMOSTAT: {},
        },
    ),
    # Combined _get_flag8 and _get_u8
    (
        (
            "R",
            v.WRITE_ACK,
            v.MSG_SCONFIG,
            int("10101010", 2).to_bytes(1, "big"),
            b"\xFF",
        ),
        {
            v.BOILER: {
                v.DATA_SLAVE_DHW_PRESENT: 0,
                v.DATA_SLAVE_CONTROL_TYPE: 1,
                v.DATA_SLAVE_COOLING_SUPPORTED: 0,
                v.DATA_SLAVE_DHW_CONFIG: 1,
                v.DATA_SLAVE_MASTER_LOW_OFF_PUMP: 0,
                v.DATA_SLAVE_CH2_PRESENT: 1,
                v.DATA_SLAVE_MEMBERID: 255,
            },
            v.OTGW: {},
            v.THERMOSTAT: {},
        },
    ),
    # _get_u16
    (
        ("A", v.READ_ACK, v.MSG_BURNSTARTS, b"\x12", b"\xAA"),
        {v.BOILER: {}, v.OTGW: {}, v.THERMOSTAT: {v.DATA_TOTAL_BURNER_STARTS: 4778}},
    ),
    # _get_s8
    (
        ("R", v.WRITE_ACK, v.MSG_TCHSETUL, b"\x50", b"\x1E"),
        {
            v.BOILER: {v.DATA_SLAVE_CH_MAX_SETP: 80, v.DATA_SLAVE_CH_MIN_SETP: 30},
            v.OTGW: {},
            v.THERMOSTAT: {},
        },
    ),
    # _get_s16
    (
        ("B", v.READ_ACK, v.MSG_TEXHAUST, b"\xFF", b"\x83"),
        {v.BOILER: {v.DATA_EXHAUST_TEMP: -125}, v.OTGW: {}, v.THERMOSTAT: {}},
    ),
)
