"""Data related to message processing"""

from . import vars as v
from .types import OpenThermMessageID, OpenThermMessageType

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
    OpenThermMessageType.READ_DATA: M2S,
    OpenThermMessageType.WRITE_DATA: M2S,
    OpenThermMessageType.READ_ACK: S2M,
    OpenThermMessageType.WRITE_ACK: S2M,
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
    OpenThermMessageID.STATUS: {
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
    OpenThermMessageID.TSET: {
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
    OpenThermMessageID.MCONFIG: {
        M2S: [{FUNC: _GET_U8, ARGS: (_LSB,), RETURNS: (v.DATA_MASTER_MEMBERID,)}],
        S2M: [],
    },
    OpenThermMessageID.SCONFIG: {
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
    OpenThermMessageID.COMMAND: {M2S: [], S2M: []},
    OpenThermMessageID.ASFFLAGS: {
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
    OpenThermMessageID.RBPFLAGS: {
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
    OpenThermMessageID.COOLING: {
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
    OpenThermMessageID.TSETC2: {
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
    OpenThermMessageID.TROVRD: {
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
    OpenThermMessageID.TSP: {M2S: [], S2M: []},
    OpenThermMessageID.TSPIDX: {M2S: [], S2M: []},
    OpenThermMessageID.FHBSIZE: {M2S: [], S2M: []},
    OpenThermMessageID.FHBIDX: {M2S: [], S2M: []},
    OpenThermMessageID.MAXRMOD: {
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
    OpenThermMessageID.MAXCAPMINMOD: {
        M2S: [],
        S2M: [
            {FUNC: _GET_U8, ARGS: (_MSB,), RETURNS: (v.DATA_SLAVE_MAX_CAPACITY,)},
            {FUNC: _GET_U8, ARGS: (_LSB,), RETURNS: (v.DATA_SLAVE_MIN_MOD_LEVEL,)},
        ],
    },
    OpenThermMessageID.TRSET: {
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
        S2M: [
            {
                FUNC: "_quirk_trset_s2m",
                ARGS: (
                    "part",
                    _MSB,
                    _LSB,
                ),
                RETURNS: (False,),
            },
        ],
    },
    OpenThermMessageID.RELMOD: {
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
    OpenThermMessageID.CHPRESS: {
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
    OpenThermMessageID.DHWFLOW: {
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
    OpenThermMessageID.TIME: {M2S: [], S2M: []},
    OpenThermMessageID.DATE: {M2S: [], S2M: []},
    OpenThermMessageID.YEAR: {M2S: [], S2M: []},
    OpenThermMessageID.TRSET2: {
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
    OpenThermMessageID.TROOM: {
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
    OpenThermMessageID.TBOILER: {
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
    OpenThermMessageID.TDHW: {
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
    OpenThermMessageID.TOUTSIDE: {
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
    OpenThermMessageID.TRET: {
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
    OpenThermMessageID.TSTOR: {
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
    OpenThermMessageID.TCOLL: {
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
    OpenThermMessageID.TFLOWCH2: {
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
    OpenThermMessageID.TDHW2: {
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
    OpenThermMessageID.TEXHAUST: {
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
    OpenThermMessageID.TDHWSETUL: {
        M2S: [],
        S2M: [
            {FUNC: _GET_S8, ARGS: (_MSB,), RETURNS: (v.DATA_SLAVE_DHW_MAX_SETP,)},
            {FUNC: _GET_S8, ARGS: (_LSB,), RETURNS: (v.DATA_SLAVE_DHW_MIN_SETP,)},
        ],
    },
    OpenThermMessageID.TCHSETUL: {
        M2S: [],
        S2M: [
            {FUNC: _GET_S8, ARGS: (_MSB,), RETURNS: (v.DATA_SLAVE_CH_MAX_SETP,)},
            {FUNC: _GET_S8, ARGS: (_LSB,), RETURNS: (v.DATA_SLAVE_CH_MIN_SETP,)},
        ],
    },
    OpenThermMessageID.OTCCURVEUL: {M2S: [], S2M: []},
    OpenThermMessageID.TDHWSET: {
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
    OpenThermMessageID.MAXTSET: {
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
    OpenThermMessageID.OTCCURVE: {M2S: [], S2M: []},
    OpenThermMessageID.STATUSVH: {
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
    OpenThermMessageID.RELVENTPOS: {
        M2S: [{FUNC: _GET_U8, ARGS: (_MSB,), RETURNS: (v.DATA_VH_CONTROL_SETPOINT,)}],
        S2M: [],
    },
    OpenThermMessageID.RELVENT: {
        M2S: [],
        S2M: [{FUNC: _GET_U8, ARGS: (_MSB,), RETURNS: (v.DATA_VH_RELATIVE_VENT,)}],
    },
    OpenThermMessageID.ROVRD: {
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
    OpenThermMessageID.OEMDIAG: {
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
    OpenThermMessageID.BURNSTARTS: {
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
    OpenThermMessageID.CHPUMPSTARTS: {
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
    OpenThermMessageID.DHWPUMPSTARTS: {
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
    OpenThermMessageID.DHWBURNSTARTS: {
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
    OpenThermMessageID.BURNHRS: {
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
    OpenThermMessageID.CHPUMPHRS: {
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
    OpenThermMessageID.DHWPUMPHRS: {
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
    OpenThermMessageID.DHWBURNHRS: {
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
    OpenThermMessageID.OTVERM: {
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
    OpenThermMessageID.OTVERS: {
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
    OpenThermMessageID.MVER: {
        M2S: [
            {FUNC: _GET_U8, ARGS: (_MSB,), RETURNS: (v.DATA_MASTER_PRODUCT_TYPE,)},
            {FUNC: _GET_U8, ARGS: (_LSB,), RETURNS: (v.DATA_MASTER_PRODUCT_VERSION,)},
        ],
        S2M: [],
    },
    OpenThermMessageID.SVER: {
        M2S: [],
        S2M: [
            {FUNC: _GET_U8, ARGS: (_MSB,), RETURNS: (v.DATA_SLAVE_PRODUCT_TYPE,)},
            {FUNC: _GET_U8, ARGS: (_LSB,), RETURNS: (v.DATA_SLAVE_PRODUCT_VERSION,)},
        ],
    },
}
