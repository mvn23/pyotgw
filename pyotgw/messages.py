"""Data related to message processing"""

from pyotgw import vars as v

_GET_FLAG8 = "_get_flag8"
_GET_FLOAT = "_get_f8_8"
_GET_S16 = "_get_s16"
_GET_S8 = "_get_s8"
_GET_U16 = "_get_u16"
_GET_U8 = "_get_u8"
_LSB = "lsb"
_MSB = "msb"

ARGS = "args"
FUNC = "function"
M2S = "m2s"
RETURNS = "returns"
S2M = "s2m"

MSG_TYPE = {
    v.READ_DATA: M2S,
    v.WRITE_DATA: M2S,
    v.READ_ACK: S2M,
    v.WRITE_ACK: S2M,
}

REGISTRY = {
    # MSG_ID = {
    #     msg_type: [
    #         {
    #             FUNC: "func_name",
    #             ARGS: (f_args,),
    #             RETURNS: (val_1, val_2, ..., val_n),
    #         },
    #     ],
    # }
    v.MSG_STATUS: {
        M2S: [
            {
                FUNC: _GET_FLAG8,
                ARGS: (_MSB,),
                RETURNS: (
                    v.DATA_MASTER_CH_ENABLED,
                    v.DATA_MASTER_DHW_ENABLED,
                    v.DATA_MASTER_COOLING_ENABLED,
                    v.DATA_MASTER_OTC_ENABLED,
                    v.DATA_MASTER_CH2_ENABLED,
                ),
            },
        ],
        S2M: [
            {
                FUNC: _GET_FLAG8,
                ARGS: (_LSB,),
                RETURNS: (
                    v.DATA_SLAVE_FAULT_IND,
                    v.DATA_SLAVE_CH_ACTIVE,
                    v.DATA_SLAVE_DHW_ACTIVE,
                    v.DATA_SLAVE_FLAME_ON,
                    v.DATA_SLAVE_COOLING_ACTIVE,
                    v.DATA_SLAVE_CH2_ACTIVE,
                    v.DATA_SLAVE_DIAG_IND,
                ),
            },
        ],
    },
    v.MSG_TSET: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_CONTROL_SETPOINT,),
            },
        ],
    },
    v.MSG_MCONFIG: {
        M2S: [{FUNC: _GET_U8, ARGS: (_LSB,), RETURNS: (v.DATA_MASTER_MEMBERID,)}],
        S2M: [],
    },
    v.MSG_SCONFIG: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLAG8,
                ARGS: (_MSB,),
                RETURNS: (
                    v.DATA_SLAVE_DHW_PRESENT,
                    v.DATA_SLAVE_CONTROL_TYPE,
                    v.DATA_SLAVE_COOLING_SUPPORTED,
                    v.DATA_SLAVE_DHW_CONFIG,
                    v.DATA_SLAVE_MASTER_LOW_OFF_PUMP,
                    v.DATA_SLAVE_CH2_PRESENT,
                ),
            },
            {FUNC: _GET_U8, ARGS: (_LSB,), RETURNS: (v.DATA_SLAVE_MEMBERID,)},
        ],
    },
    v.MSG_COMMAND: {M2S: [], S2M: []},
    v.MSG_ASFFLAGS: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLAG8,
                ARGS: (_MSB,),
                RETURNS: (
                    v.DATA_SLAVE_SERVICE_REQ,
                    v.DATA_SLAVE_REMOTE_RESET,
                    v.DATA_SLAVE_LOW_WATER_PRESS,
                    v.DATA_SLAVE_GAS_FAULT,
                    v.DATA_SLAVE_AIR_PRESS_FAULT,
                    v.DATA_SLAVE_WATER_OVERTEMP,
                ),
            },
            {FUNC: _GET_U8, ARGS: (_LSB,), RETURNS: (v.DATA_SLAVE_OEM_FAULT,)},
        ],
    },
    v.MSG_RBPFLAGS: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLAG8,
                ARGS: (_MSB,),
                RETURNS: (
                    v.DATA_REMOTE_TRANSFER_DHW,
                    v.DATA_REMOTE_TRANSFER_MAX_CH,
                ),
            },
            {
                FUNC: _GET_FLAG8,
                ARGS: (_LSB,),
                RETURNS: (
                    v.DATA_REMOTE_RW_DHW,
                    v.DATA_REMOTE_RW_MAX_CH,
                ),
            },
        ],
    },
    v.MSG_COOLING: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_COOLING_CONTROL,),
            },
        ],
    },
    v.MSG_TSETC2: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_CONTROL_SETPOINT_2,),
            },
        ],
    },
    v.MSG_TROVRD: {
        M2S: [],
        S2M: [
            {
                FUNC: "_quirk_trovrd",
                ARGS: (
                    "part",
                    "src",
                    _MSB,
                    _LSB,
                ),
                RETURNS: (False,),
            },
        ],
    },
    v.MSG_TSP: {M2S: [], S2M: []},
    v.MSG_TSPIDX: {M2S: [], S2M: []},
    v.MSG_FHBSIZE: {M2S: [], S2M: []},
    v.MSG_FHBIDX: {M2S: [], S2M: []},
    v.MSG_MAXRMOD: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_SLAVE_MAX_RELATIVE_MOD,),
            },
        ],
    },
    v.MSG_MAXCAPMINMOD: {
        M2S: [],
        S2M: [
            {FUNC: _GET_U8, ARGS: (_MSB,), RETURNS: (v.DATA_SLAVE_MAX_CAPACITY,)},
            {FUNC: _GET_U8, ARGS: (_LSB,), RETURNS: (v.DATA_SLAVE_MIN_MOD_LEVEL,)},
        ],
    },
    v.MSG_TRSET: {
        M2S: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_ROOM_SETPOINT,),
            },
        ],
        S2M: [],
    },
    v.MSG_RELMOD: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_REL_MOD_LEVEL,),
            },
        ],
    },
    v.MSG_CHPRESS: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_CH_WATER_PRESS,),
            },
        ],
    },
    v.MSG_DHWFLOW: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_DHW_FLOW_RATE,),
            },
        ],
    },
    v.MSG_TIME: {M2S: [], S2M: []},
    v.MSG_DATE: {M2S: [], S2M: []},
    v.MSG_YEAR: {M2S: [], S2M: []},
    v.MSG_TRSET2: {
        M2S: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_ROOM_SETPOINT_2,),
            },
        ],
        S2M: [],
    },
    v.MSG_TROOM: {
        M2S: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_ROOM_TEMP,),
            }
        ],
        S2M: [],
    },
    v.MSG_TBOILER: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_CH_WATER_TEMP,),
            },
        ],
    },
    v.MSG_TDHW: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_DHW_TEMP,),
            }
        ],
    },
    v.MSG_TOUTSIDE: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_OUTSIDE_TEMP,),
            },
        ],
    },
    v.MSG_TRET: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_RETURN_WATER_TEMP,),
            },
        ],
    },
    v.MSG_TSTOR: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_SOLAR_STORAGE_TEMP,),
            },
        ],
    },
    v.MSG_TCOLL: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_SOLAR_COLL_TEMP,),
            },
        ],
    },
    v.MSG_TFLOWCH2: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_CH_WATER_TEMP_2,),
            },
        ],
    },
    v.MSG_TDHW2: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_DHW_TEMP_2,),
            }
        ],
    },
    v.MSG_TEXHAUST: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_S16,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_EXHAUST_TEMP,),
            }
        ],
    },
    v.MSG_TDHWSETUL: {
        M2S: [],
        S2M: [
            {FUNC: _GET_S8, ARGS: (_MSB,), RETURNS: (v.DATA_SLAVE_DHW_MAX_SETP,)},
            {FUNC: _GET_S8, ARGS: (_LSB,), RETURNS: (v.DATA_SLAVE_DHW_MIN_SETP,)},
        ],
    },
    v.MSG_TCHSETUL: {
        M2S: [],
        S2M: [
            {FUNC: _GET_S8, ARGS: (_MSB,), RETURNS: (v.DATA_SLAVE_CH_MAX_SETP,)},
            {FUNC: _GET_S8, ARGS: (_LSB,), RETURNS: (v.DATA_SLAVE_CH_MIN_SETP,)},
        ],
    },
    v.MSG_OTCCURVEUL: {M2S: [], S2M: []},
    v.MSG_TDHWSET: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_DHW_SETPOINT,),
            },
        ],
    },
    v.MSG_MAXTSET: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_MAX_CH_SETPOINT,),
            },
        ],
    },
    v.MSG_OTCCURVE: {M2S: [], S2M: []},
    v.MSG_STATUSVH: {
        M2S: [
            {
                FUNC: _GET_FLAG8,
                ARGS: (_MSB,),
                RETURNS: (
                    v.DATA_VH_MASTER_VENT_ENABLED,
                    v.DATA_VH_MASTER_BYPASS_POS,
                    v.DATA_VH_MASTER_BYPASS_MODE,
                    v.DATA_VH_MASTER_FREE_VENT_MODE,
                ),
            },
        ],
        S2M: [
            {
                FUNC: _GET_FLAG8,
                ARGS: (_LSB,),
                RETURNS: (
                    v.DATA_VH_SLAVE_FAULT_INDICATE,
                    v.DATA_VH_SLAVE_VENT_MODE,
                    v.DATA_VH_SLAVE_BYPASS_STATUS,
                    v.DATA_VH_SLAVE_BYPASS_AUTO_STATUS,
                    v.DATA_VH_SLAVE_FREE_VENT_STATUS,
                    None,
                    v.DATA_VH_SLAVE_DIAG_INDICATE,
                ),
            },
        ],
    },
    v.MSG_RELVENTPOS: {
        M2S: [{FUNC: _GET_U8, ARGS: (_MSB,), RETURNS: (v.DATA_VH_CONTROL_SETPOINT,)}],
        S2M: [],
    },
    v.MSG_RELVENT: {
        M2S: [],
        S2M: [{FUNC: _GET_U8, ARGS: (_MSB,), RETURNS: (v.DATA_VH_RELATIVE_VENT,)}],
    },
    v.MSG_ROVRD: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLAG8,
                ARGS: (_LSB,),
                RETURNS: (
                    v.DATA_ROVRD_MAN_PRIO,
                    v.DATA_ROVRD_AUTO_PRIO,
                ),
            },
        ],
    },
    v.MSG_OEMDIAG: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_U16,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_OEM_DIAG,),
            }
        ],
    },
    v.MSG_BURNSTARTS: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_U16,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_TOTAL_BURNER_STARTS,),
            },
        ],
    },
    v.MSG_CHPUMPSTARTS: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_U16,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_CH_PUMP_STARTS,),
            },
        ],
    },
    v.MSG_DHWPUMPSTARTS: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_U16,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_DHW_PUMP_STARTS,),
            },
        ],
    },
    v.MSG_DHWBURNSTARTS: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_U16,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_DHW_BURNER_STARTS,),
            },
        ],
    },
    v.MSG_BURNHRS: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_U16,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_TOTAL_BURNER_HOURS,),
            },
        ],
    },
    v.MSG_CHPUMPHRS: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_U16,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_CH_PUMP_HOURS,),
            }
        ],
    },
    v.MSG_DHWPUMPHRS: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_U16,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_DHW_PUMP_HOURS,),
            },
        ],
    },
    v.MSG_DHWBURNHRS: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_U16,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_DHW_BURNER_HOURS,),
            },
        ],
    },
    v.MSG_OTVERM: {
        M2S: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_MASTER_OT_VERSION,),
            },
        ],
        S2M: [],
    },
    v.MSG_OTVERS: {
        M2S: [],
        S2M: [
            {
                FUNC: _GET_FLOAT,
                ARGS: (
                    _MSB,
                    _LSB,
                ),
                RETURNS: (v.DATA_SLAVE_OT_VERSION,),
            },
        ],
    },
    v.MSG_MVER: {
        M2S: [
            {FUNC: _GET_U8, ARGS: (_MSB,), RETURNS: (v.DATA_MASTER_PRODUCT_TYPE,)},
            {FUNC: _GET_U8, ARGS: (_LSB,), RETURNS: (v.DATA_MASTER_PRODUCT_VERSION,)},
        ],
        S2M: [],
    },
    v.MSG_SVER: {
        M2S: [],
        S2M: [
            {FUNC: _GET_U8, ARGS: (_MSB,), RETURNS: (v.DATA_SLAVE_PRODUCT_TYPE,)},
            {FUNC: _GET_U8, ARGS: (_LSB,), RETURNS: (v.DATA_SLAVE_PRODUCT_VERSION,)},
        ],
    },
}
