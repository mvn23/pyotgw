"""Asyncio protocol implementation for pyotgw"""
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

import pyotgw.messages as m
from pyotgw import vars as v

_LOGGER = logging.getLogger(__name__)


class OpenThermProtocol(asyncio.Protocol):
    """
    Implementation of the Opentherm Gateway protocol to be used with
    asyncio connections.
    """

    def __init__(self):
        """Initialise the protocol object."""
        self.transport = None
        self.loop = None
        self._active = False
        self._cmd_lock = asyncio.Lock()
        self._wd_lock = asyncio.Lock()
        self._cmdq = asyncio.Queue()
        self._msgq = asyncio.Queue()
        self._updateq = asyncio.Queue()
        self._readbuf = b""
        self._update_cb = None
        self._received_lines = 0
        self._msg_task = None
        self._report_task = None
        self._watchdog_task = None
        self._watchdog_cb = None
        self._watchdog_timeout = 5
        self.status = copy.deepcopy(v.DEFAULT_STATUS)
        self.connected = False

    def connection_made(self, transport):
        """Gets called when a connection to the gateway is established."""
        self.transport = transport
        self.loop = transport.loop
        self._received_lines = 0
        self._msg_task = self.loop.create_task(self._process_msgs())
        self.status = copy.deepcopy(v.DEFAULT_STATUS)
        self.connected = True

    def connection_lost(self, exc):
        """
        Gets called when the connection to the gateway is lost.
        Tear down and clean up the protocol object.
        """
        if self.active():
            _LOGGER.error("Disconnected: %s", exc)
        self._active = False
        self.connected = False
        self.transport.close()
        if self._report_task is not None:
            self._report_task.cancel()
        self._msg_task.cancel()
        for queue in [self._cmdq, self._updateq, self._msgq]:
            while not queue.empty():
                queue.get_nowait()
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
        self._active = True
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

    def setup_watchdog(self, callback, timeout):
        """Trigger a reconnect after @timeout seconds of inactivity."""
        self._watchdog_timeout = timeout
        self._watchdog_cb = callback
        self._watchdog_task = self.loop.create_task(self._watchdog(timeout))

    async def cancel_watchdog(self):
        """Cancel the watchdog task and related variables."""
        if self.watchdog_active():
            _LOGGER.debug("Canceling Watchdog task.")
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                self._watchdog_task = None

    async def _inform_watchdog(self):
        """Inform the watchdog of activity."""
        async with self._wd_lock:
            if not self.watchdog_active():
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
        await asyncio.sleep(timeout)
        _LOGGER.debug("Watchdog triggered!")
        try:
            _LOGGER.debug("Internal read buffer content: %s", self._readbuf.hex())
            _LOGGER.debug("Serial transport closing: %s", self.transport.is_closing())
            _LOGGER.debug("Serial settings: %s", self.transport.serial.get_settings())
            _LOGGER.debug(
                "Serial input buffer size: %d", self.transport.serial.in_waiting
            )
        except AttributeError as err:
            _LOGGER.debug(
                "Could not generate debug output during disconnect."
                " Reported error: %s",
                err,
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
            _LOGGER.info(
                "The OpenTherm Gateway received an erroneous message."
                " This is not a bug in pyotgw. Ignoring: %s",
                frame.hex().upper(),
            )
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

    @staticmethod
    def _get_msgtype(byte):
        """
        Return the message type of Opentherm messages according to
        byte.
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
                *[args[i].hex().upper() for i in range(2, 5)],
            )
            await self._process_msg(args)

    async def _process_msg(self, message):
        """
        Process message and update status variables where necessary.
        Add status to queue if it was changed in the process.
        """
        (
            src,
            mtype,
            msgid,
            msb,  # pylint: disable=possibly-unused-variable
            lsb,  # pylint: disable=possibly-unused-variable
        ) = message
        if msgid not in m.REGISTRY:
            return

        if src in "TA":
            statuspart = self.status[v.THERMOSTAT]
        else:  # src in "BR"
            statuspart = self.status[v.BOILER]

        for action in m.REGISTRY[msgid][m.MSG_TYPE[mtype]]:
            func = getattr(self, action[m.FUNC])
            loc = locals()
            args = (loc[arg] for arg in action[m.ARGS])
            if asyncio.iscoroutinefunction(func):
                ret = await func(*args)
            else:
                ret = func(*args)
            ret = ret if isinstance(ret, list) else [ret]
            for var, val in zip(action[m.RETURNS], ret):
                if var is False:
                    return
                if var is None:
                    continue
                statuspart[var] = val

        self._updateq.put_nowait(copy.deepcopy(self.status))

    async def _quirk_trovrd(self, statuspart, src, msb, lsb):
        """Handle MSG_TROVRD with iSense quirk"""
        ovrd_value = self._get_f8_8(msb, lsb)
        if ovrd_value > 0:
            # iSense quirk: the gateway keeps sending override value
            # even if the thermostat has cancelled the override.
            if self.status[v.OTGW].get(v.OTGW_THRM_DETECT) == "I" and src == "A":
                ovrd = await self.issue_cmd(
                    v.OTGW_CMD_REPORT, v.OTGW_REPORT_SETPOINT_OVRD
                )
                match = re.match(r"^O=(N|[CT]([0-9]+.[0-9]+))$", ovrd, re.IGNORECASE)
                if not match:
                    return
                if match.group(1) in "Nn":
                    if v.DATA_ROOM_SETPOINT_OVRD in statuspart:
                        del statuspart[v.DATA_ROOM_SETPOINT_OVRD]
                elif match.group(2):
                    statuspart[v.DATA_ROOM_SETPOINT_OVRD] = float(match.group(2))
            else:
                statuspart[v.DATA_ROOM_SETPOINT_OVRD] = ovrd_value
        elif statuspart.get(v.DATA_ROOM_SETPOINT_OVRD):
            del statuspart[v.DATA_ROOM_SETPOINT_OVRD]

        self._updateq.put_nowait(copy.deepcopy(self.status))

    @staticmethod
    def _get_flag8(byte):
        """
        Split a byte into a list of 8 bits (1/0).
        """
        ret = [0, 0, 0, 0, 0, 0, 0, 0]
        byte = byte[0]
        for i in range(0, 8):
            ret[i] = byte & 1
            byte = byte >> 1
        return ret

    @staticmethod
    def _get_u8(byte):
        """
        Convert a byte into an unsigned int.
        """
        return struct.unpack(">B", byte)[0]

    @staticmethod
    def _get_s8(byte):
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
        try:
            _LOGGER.debug("Starting reporting routine")
            while True:
                oldstatus = copy.deepcopy(self.status)
                stat = await self._updateq.get()
                if self._update_cb is not None and oldstatus != stat:
                    # Each client gets its own copy of the dict.
                    self.loop.create_task(self._update_cb(copy.deepcopy(stat)))
        except asyncio.CancelledError:
            _LOGGER.debug("Stopping reporting routine")
            self._report_task = None

    def set_update_cb(self, callback):
        """Register the update callback."""
        if self._report_task is not None and not self._report_task.cancelled():
            self._report_task.cancel()
        self._update_cb = callback
        if callback is not None:
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
            if isinstance(value, float):
                value = f"{value:.2f}"
            _LOGGER.debug("Sending command: %s with value %s", cmd, value)
            self.transport.write(f"{cmd}={value}\r\n".encode("ascii"))
            if cmd == v.OTGW_CMD_REPORT:
                expect = fr"^{cmd}:\s*([A-Z]{{2}}|{value}=[^$]+)$"
            # OTGW_CMD_CONTROL_HEATING_2 and OTGW_CMD_CONTROL_SETPOINT_2 do not adhere
            # to the standard response format (<cmd>: <value>) at the moment, but report
            # only the value. This will likely be fixed in the future, so we support
            # both formats.
            elif cmd in (
                v.OTGW_CMD_CONTROL_HEATING_2,
                v.OTGW_CMD_CONTROL_SETPOINT_2,
            ):
                expect = fr"^(?:{cmd}:\s*)?(0|1|[0-9]+\.[0-9]{{2}}|[A-Z]{{2}})$"
            else:
                expect = fr"^{cmd}:\s*([^$]+)$"

            async def send_again(err):
                """Resend the command."""
                nonlocal retry
                _LOGGER.warning("Command %s failed with %s, retrying...", cmd, err)
                retry -= 1
                self.transport.write(f"{cmd}={value}\r\n".encode("ascii"))

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
                    while not re.match(r"OpenTherm Gateway \d+(\.\d+)*", msg):
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
                else:
                    _LOGGER.warning("Unknown message in command queue: %s", msg)
                await send_again(msg)

            while True:
                msg = await self._cmdq.get()
                ret = await process(msg)
                if ret is not None:
                    return ret

    def active(self):
        """Indicate that we have seen activity on the serial line."""
        return self._active

    async def init_and_wait_for_activity(self):
        """Wait for activity on the serial connection."""
        await self.issue_cmd(v.OTGW_CMD_SUMMARY, 0, retry=0)
        while not self.active():
            await asyncio.sleep(0)
