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
import copy
import logging
import re
import struct
from asyncio.queues import QueueFull

from pyotgw import vars as v

_LOGGER = logging.getLogger(__name__)


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
        self._wd_lock = asyncio.Lock(loop=self.loop)
        self._cmdq = asyncio.Queue(loop=self.loop)
        self._msgq = asyncio.Queue(loop=self.loop)
        self._updateq = asyncio.Queue(loop=self.loop)
        self._readbuf = b""
        self._update_cb = None
        self._received_lines = 0
        self._msg_task = self.loop.create_task(self._process_msgs())
        self._report_task = None
        self._watchdog_task = None
        self.status = copy.deepcopy(v.DEFAULT_STATUS)
        self.connected = True

    def connection_lost(self, exc):
        """
        Gets called when the connection to the gateway is lost.
        Tear down and clean up the protocol object.
        """
        if self.connected:
            _LOGGER.error("Disconnected: %s", exc)
        self.connected = False
        self.transport.close()
        if self._report_task is not None:
            self._report_task.cancel()
        self._msg_task.cancel()
        for q in [self._cmdq, self._updateq, self._msgq]:
            while not q.empty():
                q.get_nowait()
        self.status = copy.deepcopy(v.DEFAULT_STATUS)
        if self._update_cb is not None:
            self.loop.create_task(self._update_cb(copy.deepcopy(self.status)))

    async def disconnect(self):
        """Disconnect gracefully."""
        if self.watchdog_active():
            await self.cancel_watchdog()
        if self.transport.is_closing() or not self.connected:
            return
        self.connected = False
        self.transport.close()

    def data_received(self, data):
        """
        Gets called when new data is received on the serial interface.
        Perform line buffering and call line_received() with complete
        lines.
        """
        # DIY line buffering...
        newline = b"\r\n"
        eot = b"\x04"
        self._readbuf += data
        while newline in self._readbuf:
            line, _, self._readbuf = self._readbuf.partition(newline)
            if line:
                if eot in line:
                    # Discard everything before EOT
                    _, _, line = line.partition(eot)
                try:
                    decoded = line.decode("ascii")
                except UnicodeDecodeError:
                    _LOGGER.debug("Invalid data received, ignoring...")
                    return
                self.line_received(decoded)

    def watchdog_active(self):
        """Return the current watchdog state."""
        return self._watchdog_task is not None

    async def setup_watchdog(self, cb, timeout):
        """Trigger a reconnect after @timeout seconds of inactivity."""
        self._watchdog_timeout = timeout
        self._watchdog_cb = cb
        self._watchdog_task = self.loop.create_task(self._watchdog(timeout))

    async def cancel_watchdog(self):
        """Cancel the watchdog task and related variables."""
        if self._watchdog_task is not None:
            _LOGGER.debug("Canceling Watchdog task.")
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                self._watchdog_task = None

    async def _inform_watchdog(self):
        """Inform the watchdog of activity."""
        async with self._wd_lock:
            if self._watchdog_task is None:
                # Check within the Lock to deal with external cancel_watchdog
                # calls with queued _inform_watchdog tasks.
                return
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                self._watchdog_task = self.loop.create_task(
                    self._watchdog(self._watchdog_timeout)
                )
                _LOGGER.debug("Watchdog timer reset!")

    async def _watchdog(self, timeout):
        """Trigger and cancel the watchdog after timeout. Call callback."""
        await asyncio.sleep(timeout, loop=self.loop)
        _LOGGER.debug("Watchdog triggered!")
        try:
            _LOGGER.debug("Internal read buffer content: %s", self._readbuf.hex())
            _LOGGER.debug("Serial transport closing: %s", self.transport.is_closing())
            _LOGGER.debug("Serial settings: %s", self.transport.serial.get_settings())
            _LOGGER.debug(
                "Serial input buffer size: %d", self.transport.serial.in_waiting
            )
        except AttributeError as e:
            _LOGGER.debug(
                "Could not generate debug output during disconnect."
                " Reported error: %s",
                e,
            )
        await self.cancel_watchdog()
        await self._watchdog_cb()

    def line_received(self, line):
        """
        Gets called by data_received() when a complete line is
        received.
        Inspect the received line and process or queue accordingly.
        """
        self._received_lines += 1
        _LOGGER.debug("Received line %d: %s", self._received_lines, line)
        self.loop.create_task(self._inform_watchdog())
        pattern = r"^(T|B|R|A|E)([0-9A-F]{8})$"
        msg = re.match(pattern, line)
        if msg:
            src, mtype, mid, msb, lsb = self._dissect_msg(msg)
            if lsb is not None:
                self._msgq.put_nowait((src, mtype, mid, msb, lsb))
                _LOGGER.debug(
                    "Added line %d to message queue. Queue size: %d",
                    self._received_lines,
                    self._msgq.qsize(),
                )
        elif re.match(r"^[0-9A-F]{1,8}$", line) and self._received_lines == 1:
            # Partial message on fresh connection. Ignore.
            self._received_lines = 0
            _LOGGER.debug("Ignoring line: %s", line)
        else:
            try:
                self._cmdq.put_nowait(line)
                _LOGGER.debug(
                    "Added line %d to command queue. Queue size: %d",
                    self._received_lines,
                    self._cmdq.qsize(),
                )
            except QueueFull:
                _LOGGER.error("Queue full, discarded message: %s", line)

    def _dissect_msg(self, match):
        """
        Split messages into bytes and return a tuple of bytes.
        """
        recvfrom = match.group(1)
        frame = bytes.fromhex(match.group(2))
        if recvfrom == "E":
            _LOGGER.warning("Received erroneous message, ignoring: %s", frame)
            return (None, None, None, None, None)
        msgtype = self._get_msgtype(frame[0])
        if msgtype in (v.READ_ACK, v.WRITE_ACK, v.READ_DATA, v.WRITE_DATA):
            # Some info is best read from the READ/WRITE_DATA messages
            # as the boiler may not support the data ID.
            # Slice syntax is used to prevent implicit cast to int.
            data_id = frame[1:2]
            data_msb = frame[2:3]
            data_lsb = frame[3:4]
            return (recvfrom, msgtype, data_id, data_msb, data_lsb)
        return (None, None, None, None, None)

    def _get_msgtype(self, byte):
        """
        Return the message type of Opentherm messages according to
        byte 1.
        """
        return (byte >> 4) & 0x7

    async def _process_msgs(self):
        """
        Get messages from the queue and pass them to _process_msg().
        Make sure we process one message at a time to keep them in sequence.
        """
        while True:
            args = await self._msgq.get()
            _LOGGER.debug(
                "Processing: %s %02x %s %s %s",
                args[0],
                args[1],
                *[args[i].hex() for i in range(2, 5)],
            )
            await self._process_msg(*args)

    async def _process_msg(self, src, msgtype, msgid, msb, lsb):  # noqa: C901
        """
        Process message and update status variables where necessary.
        Add status to queue if it was changed in the process.
        """
        if src in "TA":
            statuspart = self.status[v.THERMOSTAT]
        else:  # src in "BR"
            statuspart = self.status[v.BOILER]

        if msgtype in (v.READ_DATA, v.WRITE_DATA):
            # Data sent from thermostat
            if msgid == v.MSG_STATUS:
                # Master sends status
                thermo_status = self._get_flag8(msb)
                statuspart[v.DATA_MASTER_CH_ENABLED] = thermo_status[0]
                statuspart[v.DATA_MASTER_DHW_ENABLED] = thermo_status[1]
                statuspart[v.DATA_MASTER_COOLING_ENABLED] = thermo_status[2]
                statuspart[v.DATA_MASTER_OTC_ENABLED] = thermo_status[3]
                statuspart[v.DATA_MASTER_CH2_ENABLED] = thermo_status[4]
            elif msgid == v.MSG_MCONFIG:
                # Master sends ID
                statuspart[v.DATA_MASTER_MEMBERID] = self._get_u8(lsb)
            elif msgid == v.MSG_TRSET:
                # Master changes room setpoint, support by the boiler
                # is not mandatory, but we want the data regardless
                statuspart[v.DATA_ROOM_SETPOINT] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_TRSET2:
                # Master changes room setpoint 2, support by the boiler
                # is not mandatory, but we want the data regardless
                statuspart[v.DATA_ROOM_SETPOINT_2] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_TROOM:
                # Master reports sensed room temperature
                statuspart[v.DATA_ROOM_TEMP] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_OTVERM:
                # Master reports OpenTherm version
                statuspart[v.DATA_MASTER_OT_VERSION] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_MVER:
                # Master reports product type and version
                statuspart[v.DATA_MASTER_PRODUCT_TYPE] = self._get_u8(msb)
                statuspart[v.DATA_MASTER_PRODUCT_VERSION] = self._get_u8(lsb)
        elif msgtype in (v.READ_ACK, v.WRITE_ACK):
            # Data sent from boiler
            if msgid == v.MSG_STATUS:
                # Slave reports status
                boiler_status = self._get_flag8(lsb)
                statuspart[v.DATA_SLAVE_FAULT_IND] = boiler_status[0]
                statuspart[v.DATA_SLAVE_CH_ACTIVE] = boiler_status[1]
                statuspart[v.DATA_SLAVE_DHW_ACTIVE] = boiler_status[2]
                statuspart[v.DATA_SLAVE_FLAME_ON] = boiler_status[3]
                statuspart[v.DATA_SLAVE_COOLING_ACTIVE] = boiler_status[4]
                statuspart[v.DATA_SLAVE_CH2_ACTIVE] = boiler_status[5]
                statuspart[v.DATA_SLAVE_DIAG_IND] = boiler_status[6]
            elif msgid == v.MSG_TSET:
                # Slave confirms CH water setpoint
                statuspart[v.DATA_CONTROL_SETPOINT] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_SCONFIG:
                # Slave reports config and ID
                slave_status = self._get_flag8(msb)
                statuspart[v.DATA_SLAVE_DHW_PRESENT] = slave_status[0]
                statuspart[v.DATA_SLAVE_CONTROL_TYPE] = slave_status[1]
                statuspart[v.DATA_SLAVE_COOLING_SUPPORTED] = slave_status[2]
                statuspart[v.DATA_SLAVE_DHW_CONFIG] = slave_status[3]
                statuspart[v.DATA_SLAVE_MASTER_LOW_OFF_PUMP] = slave_status[4]
                statuspart[v.DATA_SLAVE_CH2_PRESENT] = slave_status[5]
                statuspart[v.DATA_SLAVE_MEMBERID] = self._get_u8(lsb)
            elif msgid == v.MSG_COMMAND:
                # TODO: implement command notification system
                pass
            elif msgid == v.MSG_ASFFLAGS:
                # Slave reports fault flags
                fault_flags = self._get_flag8(msb)
                statuspart[v.DATA_SLAVE_SERVICE_REQ] = fault_flags[0]
                statuspart[v.DATA_SLAVE_REMOTE_RESET] = fault_flags[1]
                statuspart[v.DATA_SLAVE_LOW_WATER_PRESS] = fault_flags[2]
                statuspart[v.DATA_SLAVE_GAS_FAULT] = fault_flags[3]
                statuspart[v.DATA_SLAVE_AIR_PRESS_FAULT] = fault_flags[4]
                statuspart[v.DATA_SLAVE_WATER_OVERTEMP] = fault_flags[5]
                statuspart[v.DATA_SLAVE_OEM_FAULT] = self._get_u8(lsb)
            elif msgid == v.MSG_RBPFLAGS:
                # Slave reports remote parameters
                transfer_flags = self._get_flag8(msb)
                rw_flags = self._get_flag8(lsb)
                statuspart[v.DATA_REMOTE_TRANSFER_DHW] = transfer_flags[0]
                statuspart[v.DATA_REMOTE_TRANSFER_MAX_CH] = transfer_flags[1]
                statuspart[v.DATA_REMOTE_RW_DHW] = rw_flags[0]
                statuspart[v.DATA_REMOTE_RW_MAX_CH] = rw_flags[1]
            elif msgid == v.MSG_COOLING:
                # Only report cooling control signal if slave acks it
                statuspart[v.DATA_COOLING_CONTROL] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_TSETC2:
                # Slave confirms CH2 water setpoint
                statuspart[v.DATA_CONTROL_SETPOINT_2] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_TROVRD:
                # OTGW (or downstream device) reports remote override
                ovrd_value = self._get_f8_8(msb, lsb)
                if ovrd_value > 0:
                    # iSense quirk: the gateway keeps sending override value
                    # even if the thermostat has cancelled the override.
                    if (
                        self.status[v.OTGW].get(v.OTGW_THRM_DETECT) == "I"
                        and src == "A"
                    ):
                        ovrd = await self.issue_cmd(
                            v.OTGW_CMD_REPORT, v.OTGW_REPORT_SETPOINT_OVRD
                        )
                        match = re.match(
                            r"^O=(N|[CT]([0-9]+.[0-9]+))$", ovrd, re.IGNORECASE
                        )
                        if not match:
                            return
                        if match.group(1) in "Nn":
                            if v.DATA_ROOM_SETPOINT_OVRD in statuspart:
                                del statuspart[v.DATA_ROOM_SETPOINT_OVRD]
                        elif match.group(2):
                            statuspart[v.DATA_ROOM_SETPOINT_OVRD] = float(
                                match.group(2)
                            )
                    else:
                        statuspart[v.DATA_ROOM_SETPOINT_OVRD] = ovrd_value
                elif statuspart.get(v.DATA_ROOM_SETPOINT_OVRD):
                    del statuspart[v.DATA_ROOM_SETPOINT_OVRD]
            elif msgid == v.MSG_MAXRMOD:
                # Slave reports maximum modulation level
                statuspart[v.DATA_SLAVE_MAX_RELATIVE_MOD] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_MAXCAPMINMOD:
                # Slave reports max capaxity and min modulation level
                statuspart[v.DATA_SLAVE_MAX_CAPACITY] = self._get_u8(msb)
                statuspart[v.DATA_SLAVE_MIN_MOD_LEVEL] = self._get_u8(lsb)
            elif msgid == v.MSG_RELMOD:
                # Slave reports relative modulation level
                statuspart[v.DATA_REL_MOD_LEVEL] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_CHPRESS:
                # Slave reports CH circuit pressure
                statuspart[v.DATA_CH_WATER_PRESS] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_DHWFLOW:
                # Slave reports DHW flow rate
                statuspart[v.DATA_DHW_FLOW_RATE] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_TBOILER:
                # Slave reports CH water temperature
                statuspart[v.DATA_CH_WATER_TEMP] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_TDHW:
                # Slave reports DHW temperature
                statuspart[v.DATA_DHW_TEMP] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_TOUTSIDE:
                # OTGW (or downstream device) reports outside temperature
                statuspart[v.DATA_OUTSIDE_TEMP] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_TRET:
                # Slave reports return water temperature
                statuspart[v.DATA_RETURN_WATER_TEMP] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_TSTOR:
                # Slave reports solar storage temperature
                statuspart[v.DATA_SOLAR_STORAGE_TEMP] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_TCOLL:
                # Slave reports solar collector temperature
                statuspart[v.DATA_SOLAR_COLL_TEMP] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_TFLOWCH2:
                # Slave reports CH2 water temperature
                statuspart[v.DATA_CH_WATER_TEMP_2] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_TDHW2:
                # Slave reports DHW2 temperature
                statuspart[v.DATA_DHW_TEMP_2] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_TEXHAUST:
                # Slave reports exhaust temperature
                statuspart[v.DATA_EXHAUST_TEMP] = self._get_s16(msb, lsb)
            elif msgid == v.MSG_TDHWSETUL:
                # Slave reports min/max DHW setpoint
                statuspart[v.DATA_SLAVE_DHW_MAX_SETP] = self._get_s8(msb)
                statuspart[v.DATA_SLAVE_DHW_MIN_SETP] = self._get_s8(lsb)
            elif msgid == v.MSG_TCHSETUL:
                # Slave reports min/max CH setpoint
                statuspart[v.DATA_SLAVE_CH_MAX_SETP] = self._get_s8(msb)
                statuspart[v.DATA_SLAVE_CH_MIN_SETP] = self._get_s8(lsb)
            elif msgid == v.MSG_TDHWSET:
                # Slave reports or acks DHW setpoint
                statuspart[v.DATA_DHW_SETPOINT] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_MAXTSET:
                # Slave reports or acks max CH setpoint
                statuspart[v.DATA_MAX_CH_SETPOINT] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_ROVRD:
                # OTGW (or downstream device) reports remote override
                # behaviour
                rovrd_flags = self._get_flag8(lsb)
                statuspart[v.DATA_ROVRD_MAN_PRIO] = rovrd_flags[0]
                statuspart[v.DATA_ROVRD_AUTO_PRIO] = rovrd_flags[1]
            elif msgid == v.MSG_OEMDIAG:
                # Slave reports diagnostic info
                statuspart[v.DATA_OEM_DIAG] = self._get_u16(msb, lsb)
            elif msgid == v.MSG_BURNSTARTS:
                # Slave reports burner starts
                statuspart[v.DATA_TOTAL_BURNER_STARTS] = self._get_u16(msb, lsb)
            elif msgid == v.MSG_CHPUMPSTARTS:
                # Slave reports CH pump starts
                statuspart[v.DATA_CH_PUMP_STARTS] = self._get_u16(msb, lsb)
            elif msgid == v.MSG_DHWPUMPSTARTS:
                # Slave reports DHW pump starts
                statuspart[v.DATA_DHW_PUMP_STARTS] = self._get_u16(msb, lsb)
            elif msgid == v.MSG_DHWBURNSTARTS:
                # Slave reports DHW burner starts
                statuspart[v.DATA_DHW_BURNER_STARTS] = self._get_u16(msb, lsb)
            elif msgid == v.MSG_BURNHRS:
                # Slave reports CH burner hours
                statuspart[v.DATA_TOTAL_BURNER_HOURS] = self._get_u16(msb, lsb)
            elif msgid == v.MSG_CHPUMPHRS:
                # Slave reports CH pump hours
                statuspart[v.DATA_CH_PUMP_HOURS] = self._get_u16(msb, lsb)
            elif msgid == v.MSG_DHWPUMPHRS:
                # Slave reports DHW pump hours
                statuspart[v.DATA_DHW_PUMP_HOURS] = self._get_u16(msb, lsb)
            elif msgid == v.MSG_DHWBURNHRS:
                # Slave reports DHW burner hours
                statuspart[v.DATA_DHW_BURNER_HOURS] = self._get_u16(msb, lsb)
            elif msgid == v.MSG_OTVERS:
                # Slave reports OpenTherm version
                statuspart[v.DATA_SLAVE_OT_VERSION] = self._get_f8_8(msb, lsb)
            elif msgid == v.MSG_SVER:
                # Slave reports product type and version
                statuspart[v.DATA_SLAVE_PRODUCT_TYPE] = self._get_u8(msb)
                statuspart[v.DATA_SLAVE_PRODUCT_VERSION] = self._get_u8(lsb)
        self._updateq.put_nowait(copy.deepcopy(self.status))

    def _get_flag8(self, byte):
        """
        Split a byte into a list of 8 bits (1/0).
        """
        ret = [0, 0, 0, 0, 0, 0, 0, 0]
        byte = byte[0]
        for i in range(0, 8):
            ret[i] = byte & 1
            byte = byte >> 1
        return ret

    def _get_u8(self, byte):
        """
        Convert a byte into an unsigned int.
        """
        return struct.unpack(">B", byte)[0]

    def _get_s8(self, byte):
        """
        Convert a byte into a signed int.
        """
        return struct.unpack(">b", byte)[0]

    def _get_f8_8(self, msb, lsb):
        """
        Convert 2 bytes into an OpenTherm f8_8 (float) value.
        """
        return float(self._get_s16(msb, lsb) / 256)

    def _get_u16(self, msb, lsb):
        """
        Convert 2 bytes into an unsigned int.
        """
        buf = struct.pack(">BB", self._get_u8(msb), self._get_u8(lsb))
        return int(struct.unpack(">H", buf)[0])

    def _get_s16(self, msb, lsb):
        """
        Convert 2 bytes into a signed int.
        """
        buf = struct.pack(">bB", self._get_s8(msb), self._get_u8(lsb))
        return int(struct.unpack(">h", buf)[0])

    async def _report(self):
        """
        Call _update_cb with the status dict as an argument whenever a status
        update occurs.

        This method is a coroutine
        """
        while True:
            oldstatus = copy.deepcopy(self.status)
            stat = await self._updateq.get()
            if self._update_cb is not None and oldstatus != stat:
                # Each client gets its own copy of the dict.
                self.loop.create_task(self._update_cb(copy.deepcopy(stat)))

    async def set_update_cb(self, cb):
        """Register the update callback."""
        if self._report_task is not None and not self._report_task.cancelled():
            self.loop.create_task(self._report_task.cancel())
        self._update_cb = cb
        if cb is not None:
            self._report_task = self.loop.create_task(self._report())

    async def issue_cmd(self, cmd, value, retry=3):
        """
        Issue a command, then await and return the return value.

        This method is a coroutine
        """
        async with self._cmd_lock:
            if not self.connected:
                _LOGGER.debug("Serial transport closed, not sending command %s", cmd)
                return
            while not self._cmdq.empty():
                _LOGGER.debug(
                    "Clearing leftover message from command queue: %s",
                    await self._cmdq.get(),
                )
            _LOGGER.debug("Sending command: %s with value %s", cmd, value)
            self.transport.write(f"{cmd}={value}\r\n".encode("ascii"))
            if cmd == v.OTGW_CMD_REPORT:
                expect = fr"^{cmd}:\s*([A-Z]{{2}}|{value}=[^$]+)$"
            else:
                expect = fr"^{cmd}:\s*([^$]+)$"

            async def send_again(err):
                """Resend the command."""
                nonlocal retry
                _LOGGER.warning("Command %s failed with %s, retrying...", cmd, err)
                retry -= 1
                written = self.transport.write(f"{cmd}={value}\r\n".encode("ascii"))
                _LOGGER.debug("Wrote %d bytes to serial transport", written)

            async def process(msg):
                """Process a possible response."""
                _LOGGER.debug("Got possible response for command %s: %s", cmd, msg)
                if msg in v.OTGW_ERRS:
                    # Some errors appear by themselves on one line.
                    if retry == 0:
                        raise v.OTGW_ERRS[msg]
                    await send_again(msg)
                    return
                if cmd == v.OTGW_CMD_MODE and value == "R":
                    # Device was reset, msg contains build info
                    while not re.match(r"OpenTherm Gateway \d+\.\d+\.\d+", msg):
                        msg = await self._cmdq.get()
                    return True
                match = re.match(expect, msg)
                if match:
                    if match.group(1) in v.OTGW_ERRS:
                        # Some errors are considered a response.
                        if retry == 0:
                            raise v.OTGW_ERRS[match.group(1)]
                        await send_again(msg)
                        return
                    ret = match.group(1)
                    if cmd == v.OTGW_CMD_SUMMARY and ret == "1":
                        # Expects a second line
                        part2 = await self._cmdq.get()
                        ret = [ret, part2]
                    return ret
                if re.match(r"Error 0[1-4]", msg):
                    _LOGGER.warning(
                        "Received %s. If this happens during a "
                        "reset of the gateway it can be safely "
                        "ignored.",
                        msg,
                    )
                    return
                _LOGGER.warning("Unknown message in command queue: %s", msg)
                await send_again(msg)

            while True:
                msg = await self._cmdq.get()
                ret = await process(msg)
                if ret is not None:
                    return ret
