# This file is part of pyotgw.
#
# pyotgw is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyotgw is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyotgw.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2018 Milan van Nugteren
#

import asyncio
import re
import struct
from asyncio.queues import QueueFull
from pyotgw.vars import *

from datetime import datetime


class protocol(asyncio.Protocol):
    """
    Implementation of the Opentherm Gateway protocol to be used with
    asyncio connections.
    """
    
    def connection_made(self, transport):
        """
        Gets called when a connection to the gateway is established.
        Initialise the protocol object.
        """
        self.transport = transport
        self.loop = transport.loop
        self._cmd_lock = asyncio.Lock(loop=self.loop)
        self._cmdq = asyncio.Queue(loop=self.loop)
        self._updateq = asyncio.Queue(loop=self.loop)
        self._readbuf = ''
        self._notify = []
        self.status = {}


    def data_received(self, data):
        """
        Gets called when new data is received on the serial interface.
        Perform line buffering and call line_received() with complete
        lines.
        """
        # DIY line buffering...
        self._readbuf += data.decode()
        while '\r\n' in self._readbuf:
            line, _, self._readbuf = self._readbuf.partition('\r\n')
            self.line_received(line)
    

    def line_received(self, line):
        """
        Gets called by data_received() when a complete line is
        received.
        Inspect the received line and process or queue accordingly.
        """
        pattern = r'^(T|B|R|A|E)([0-9A-F]{8})$'
        msg = re.match(pattern, line)
        try:
            if msg:
                mtype, mid, msb, lsb = self._dissect_msg(msg)
                if lsb is not None:
                    self._process_msg(mtype, mid, msb, lsb)
            else:
                self._handle_response(line)
                self._cmdq.put_nowait(line)
        except QueueFull:
            print('pyotgw: Queue full, discarded message: {}'.format(line))
            
                    
    def _handle_response(self, resp):
        """
        Handle command response and update applicable status
        variables where necessary.
        """
        ans, _, val = resp.partition(": ")
        if val is not None and ans in OTGW_CMDS:
            if OTGW_CMDS[ans] is not None:
                setattr(self, OTGW_CMDS[ans], val)

    
    def _dissect_msg(self, match):
        """
        Split messages into bytes and return a tuple of bytes.
        """
        recvfrom = match.group(1)
        frame = bytes.fromhex(match.group(2))
        if recvfrom is 'E':
            print("pyotgw: Received erroneous message, ignoring:", frame)
            return (None, None, None, None)
        msgtype = self._get_msgtype(frame[0])
        if msgtype in (READ_ACK, WRITE_ACK, READ_DATA, WRITE_DATA):
            # Some info is best read from the READ/WRITE_DATA messages
            # as the boiler may not support the data ID.
            # Slice syntax is used to prevent implicit cast to int.
            data_id = frame[1:2]
            data_msb = frame[2:3]
            data_lsb = frame[3:4]
            return (msgtype, data_id, data_msb, data_lsb)
        return (None, None, None, None)

    
    def _get_msgtype(self, byte):
        """
        Return the message type of Opentherm messages according to
        byte 1.
        """
        return (byte >> 4) & 0x7
    
    
    def _process_msg(self, msgtype, msgid, msb, lsb):
        """
        Process message and update status variables where necessary.
        Add status to queue if it was changed in the process.
        """
        oldstatus = dict(self.status)
        if msgtype in (READ_DATA, WRITE_DATA):
            # Data sent from thermostat
            if msgid == MSG_STATUS:
                # Master sends status
                thermo_status = self._get_flag8(msb)
                self.status[DATA_MASTER_CH_ENABLED] = thermo_status[0] 
                self.status[DATA_MASTER_DHW_ENABLED] = thermo_status[1]
                self.status[DATA_MASTER_COOLING_ENABLED] = thermo_status[2]
                self.status[DATA_MASTER_OTC_ENABLED] = thermo_status[3]
                self.status[DATA_MASTER_CH2_ENABLED] = thermo_status[4]
            elif msgid == MSG_MCONFIG:
                # Master sends ID
                self.status[DATA_MASTER_MEMBERID] = self._get_u8(lsb)
            elif msgid == MSG_TRSET:
                # Master changes room setpoint, support by the boiler
                # is not mandatory, but we want the data regardless
                self.status[DATA_ROOM_SETPOINT] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_TRSET2:
                # Master changes room setpoint 2, support by the boiler
                # is not mandatory, but we want the data regardless
                self.status[DATA_ROOM_SETPOINT_2] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_TROOM:
                # Master reports sensed room temperature
                self.status[DATA_ROOM_TEMP] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_OTVERM:
                # Master reports OpenTherm version
                self.status[DATA_MASTER_OT_VERSION] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_MVER:
                # Master reports product type and version
                self.status[DATA_MASTER_PRODUCT_TYPE] = self._get_u8(msb)
                self.status[DATA_MASTER_PRODUCT_VERSION] = self._get_u8(lsb)
        elif msgtype in (READ_ACK, WRITE_ACK):
            # Data sent from boiler
            if msgid == MSG_STATUS:
                # Slave reports status
                boiler_status = self._get_flag8(lsb)
                self.status[DATA_SLAVE_FAULT_IND] = boiler_status[0] 
                self.status[DATA_SLAVE_CH_ACTIVE] = boiler_status[1] 
                self.status[DATA_SLAVE_DHW_ACTIVE] = boiler_status[2] 
                self.status[DATA_SLAVE_FLAME_ON] = boiler_status[3] 
                self.status[DATA_SLAVE_COOLING_ACTIVE] = boiler_status[4] 
                self.status[DATA_SLAVE_CH2_ACTIVE] = boiler_status[5] 
                self.status[DATA_SLAVE_DIAG_IND] = boiler_status[6]
            elif msgid == MSG_TSET:
                # Slave confirms CH water setpoint
                self.status[DATA_CONTROL_SETPOINT] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_SCONFIG:
                # Slave reports config and ID
                slave_status = self._get_flag8(msb)
                self.status[DATA_SLAVE_DHW_PRESENT] = slave_status[0]
                self.status[DATA_SLAVE_CONTROL_TYPE] = slave_status[1]
                self.status[DATA_SLAVE_COOLING_SUPPORTED] = slave_status[2]
                self.status[DATA_SLAVE_DHW_CONFIG] = slave_status[3]
                self.status[DATA_SLAVE_MASTER_LOW_OFF_PUMP] = slave_status[4]
                self.status[DATA_SLAVE_CH2_PRESENT] = slave_status[5]
                self.status[DATA_SLAVE_MEMBERID] = self._get_u8(lsb)
            elif msgid == MSG_COMMAND:
                # TODO: implement command notification system
                pass
            elif msgid == MSG_ASFFLAGS:
                # Slave reports fault flags
                fault_flags = self._get_flag8(msb)
                self.status[DATA_SLAVE_SERVICE_REQ] = fault_flags[0]
                self.status[DATA_SLAVE_REMOTE_RESET] = fault_flags[1]
                self.status[DATA_SLAVE_LOW_WATER_PRESS] = fault_flags[2]
                self.status[DATA_SLAVE_GAS_FAULT] = fault_flags[3]
                self.status[DATA_SLAVE_AIR_PRESS_FAULT] = fault_flags[4]
                self.status[DATA_SLAVE_WATER_OVERTEMP] = fault_flags[5]
                self.status[DATA_SLAVE_OEM_FAULT] = self._get_u8(lsb)
            elif msgid == MSG_RBPFLAGS:
                # Slave reports remote parameters
                transfer_flags = self._get_flag8(msb)
                rw_flags = self._get_flag8(lsb)
                self.status[DATA_REMOTE_TRANSFER_DHW] = transfer_flags[0]
                self.status[DATA_REMOTE_TRANSFER_MAX_CH] = transfer_flags[1]
                self.status[DATA_REMOTE_RW_DHW] = rw_flags[0]
                self.status[DATA_REMOTE_RW_MAX_CH] = rw_flags[1]
            elif msgid == MSG_COOLING:
                # Only report cooling control signal if slave acks it
                self.status[DATA_COOLING_CONTROL] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_TSETC2:
                # Slave confirms CH2 water setpoint
                self.status[DATA_CONTROL_SETPOINT_2] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_TROVRD:
                # OTGW (or downstream device) reports remote override
                ovrd_value = self._get_f8_8(msb, lsb)
                self.status[DATA_ROOM_SETPOINT_OVRD] = (
                        ovrd_value if ovrd_value > 0 else None)
            elif msgid == MSG_MAXRMOD:
                # Slave reports maximum modulation level
                self.status[DATA_SLAVE_MAX_RELATIVE_MOD] = self._get_f8_8(
                        msb, lsb)
            elif msgid == MSG_MAXCAPMINMOD:
                # Slave reports max capaxity and min modulation level
                self.status[DATA_SLAVE_MAX_CAPACITY] = self._get_u8(msb)
                self.status[DATA_SLAVE_MIN_MOD_LEVEL] = self._get_u8(lsb)
            elif msgid == MSG_RELMOD:
                # Slave reports relative modulation level
                self.status[DATA_REL_MOD_LEVEL] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_CHPRESS:
                # Slave reports CH circuit pressure
                self.status[DATA_CH_WATER_PRESS] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_DHWFLOW:
                # Slave reports DHW flow rate
                self.status[DATA_DHW_FLOW_RATE] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_TBOILER:
                # Slave reports CH water temperature
                self.status[DATA_CH_WATER_TEMP] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_TDHW:
                # Slave reports DHW temperature
                self.status[DATA_DHW_TEMP] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_TOUTSIDE:
                # OTGW (or downstream device) reports outside temperature
                self.status[DATA_OUTSIDE_TEMP] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_TRET:
                # Slave reports return water temperature
                self.status[DATA_RETURN_WATER_TEMP] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_TSTOR:
                # Slave reports solar storage temperature
                self.status[DATA_SOLAR_STORAGE_TEMP] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_TCOLL:
                # Slave reports solar collector temperature
                self.status[DATA_SOLAR_COLL_TEMP] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_TFLOWCH2:
                # Slave reports CH2 water temperature
                self.status[DATA_CH_WATER_TEMP_2] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_TDHW2:
                # Slave reports DHW2 temperature
                self.status[DATA_DHW_TEMP_2] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_TEXHAUST:
                # Slave reports exhaust temperature
                self.status[DATA_EXHAUST_TEMP] = self._get_s16(msb, lsb)
            elif msgid == MSG_TDHWSETUL:
                # Slave reports min/max DHW setpoint
                self.status[DATA_SLAVE_DHW_MAX_SETP] = self._get_s8(msb)
                self.status[DATA_SLAVE_DHW_MIN_SETP] = self._get_s8(lsb)
            elif msgid == MSG_TCHSETUL:
                # Slave reports min/max CH setpoint
                self.status[DATA_SLAVE_CH_MAX_SETP] = self._get_s8(msb)
                self.status[DATA_SLAVE_CH_MIN_SETP] = self._get_s8(lsb)
            elif msgid == MSG_TDHWSET:
                # Slave reports or acks DHW setpoint
                self.status[DATA_DHW_SETPOINT] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_MAXTSET:
                # Slave reports or acks max CH setpoint
                self.status[DATA_MAX_CH_SETPOINT] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_ROVRD:
                # OTGW (or downstream device) reports remote override
                # behaviour
                rovrd_flags = self._get_flag8(lsb)
                self.status[DATA_ROVRD_MAN_PRIO] = rovrd_flags[0]
                self.status[DATA_ROVRD_AUTO_PRIO] = rovrd_flags[1]
            elif msgid == MSG_OEMDIAG:
                # Slave reports diagnostic info
                self.status[DATA_OEM_DIAG] = self._get_u16(msb, lsb)
            elif msgid == MSG_BURNSTARTS:
                # Slave reports burner starts
                self.status[DATA_CH_BURNER_STARTS] = self._get_u16(msb, lsb)
            elif msgid == MSG_CHPUMPSTARTS:
                # Slave reports CH pump starts
                self.status[DATA_CH_PUMP_STARTS] = self._get_u16(msb, lsb)
            elif msgid == MSG_DHWPUMPSTARTS:
                # Slave reports DHW pump starts
                self.status[DATA_DHW_PUMP_STARTS] = self._get_u16(msb, lsb)
            elif msgid == MSG_DHWBURNSTARTS:
                # Slave reports DHW burner starts
                self.status[DATA_DHW_BURNER_STARTS] = self._get_u16(msb, lsb)
            elif msgid == MSG_CHBURNHRS:
                # Slave reports CH burner hours
                self.status[DATA_CH_BURNER_HOURS] = self._get_u16(msb, lsb)
            elif msgid == MSG_CHPUMPHRS:
                # Slave reports CH pump hours
                self.status[DATA_CH_PUMP_HOURS] = self._get_u16(msb, lsb)
            elif msgid == MSG_DHWPUMPHRS:
                # Slave reports DHW pump hours
                self.status[DATA_DHW_PUMP_HOURS] = self._get_u16(msb, lsb)
            elif msgid == MSG_DHWBURNHRS:
                # Slave reports DHW burner hours
                self.status[DATA_DHW_BURNER_HOURS] = self._get_u16(msb, lsb)
            elif msgid == MSG_OTVERS:
                # Slave reports OpenTherm version
                self.status[DATA_SLAVE_OT_VERSION] = self._get_f8_8(msb, lsb)
            elif msgid == MSG_SVER:
                # Slave reports product type and version
                self.status[DATA_SLAVE_PRODUCT_TYPE] = self._get_u8(msb)
                self.status[DATA_SLAVE_PRODUCT_VERSION] = self._get_u8(lsb)
        if self.status != oldstatus:
            self._updateq.put_nowait(self.status)


    def _get_flag8(self, byte):
        """
        Split a byte into a list of 8 bits (1/0).
        """
        ret = [0, 0, 0, 0, 0, 0, 0, 0]
        byte = byte[0]
        for i in range(0, 8):
            ret[i] = (byte & 1)
            byte = byte >> 1
        return ret
    
    
    def _get_u8(self, byte):
        """
        Convert a byte into an unsigned int.
        """
        return struct.unpack('>B', byte)[0]

    
    def _get_s8(self, byte):
        """
        Convert a byte into a signed int.
        """
        return struct.unpack('>b', byte)[0]
    
    
    def _get_f8_8(self, msb, lsb):
        """
        Convert 2 bytes into an OpenTherm f8_8 (float) value.
        """
        return float(self._get_s16(msb, lsb)/256)

    
    def _get_u16(self, msb, lsb):
        """
        Convert 2 bytes into an unsigned int.
        """
        buf = struct.pack('>BB', self._get_u8(msb), self._get_u8(lsb))
        return int(struct.unpack('>H', buf)[0])

    
    def _get_s16(self, msb, lsb):
        """
        Convert 2 bytes into a signed int.
        """
        buf = struct.pack('>bB', self._get_s8(msb), self._get_u8(lsb))
        return int(struct.unpack('>h', buf)[0])
    
    
    async def _report(self):
        """
        Call all subscribed coroutines in _notify whenever a status
        update occurs.

        This method is a coroutine
        """
        while True:
            stat = await self._updateq.get()
            if len(self._notify) > 0:
                self.status["date"] = datetime.now()
                asyncio.gather(*[coro(stat) for coro in self._notify],
                               loop=self.loop)
        
    
    async def issue_cmd(self, cmd, value):
        """
        Issue a command, then await and return the return value.

        This method is a coroutine
        """
        with (await self._cmd_lock):
            self.transport.write('{}={}\r\n'
                                 .format(cmd, value).encode('ascii'))
            expect = r'^{}:\s*([^$]+)$'.format(cmd)
            while True:
                msg = await self._cmdq.get()
                match = re.match(expect, msg)
                if match:
                    if match.group(1) in OTGW_ERRS:
                        raise OTGW_ERRS[msg]
                    ret = match.group(1)
                    if cmd is OTGW_CMD_SUMMARY and ret is '1':
                        # Expects a second line
                        part2 = await self._cmdq.get()
                        ret = [ret, part2]
                    return ret
                elif cmd is OTGW_CMD_MODE and value is 'R':
                    # Device was reset, msg contains build info
                    while not re.match(r'OpenTherm Gateway \d+\.\d+\.\d+',
                                       msg):
                        msg = await self._cmdq.get()
                    return True
                else:
                    print("pyotgw: Unknown message",
                          "in command queue: {}".format(msg))
                
                
    