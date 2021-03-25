"""Asyncio protocol implementation for pyotgw"""

import asyncio
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

    def __init__(self, status_manager, activity_callback):
        """Initialise the protocol object."""
        self.transport = None
        self.loop = None
        self._active = False
        self._cmd_lock = asyncio.Lock()
        self._cmdq = asyncio.Queue()
        self._msgq = asyncio.Queue()
        self._readbuf = b""
        self._received_lines = 0
        self._msg_task = None
        self.activity_callback = activity_callback
        self._connected = False
        self.status_manager = status_manager

    def connection_made(self, transport):
        """Gets called when a connection to the gateway is established."""
        self.transport = transport
        self.loop = transport.loop
        self._received_lines = 0
        self._msg_task = self.loop.create_task(self._process_msgs())
        self._connected = True

    def connection_lost(self, exc):
        """
        Gets called when the connection to the gateway is lost.
        Tear down and clean up the protocol object.
        """
        if self.active:
            _LOGGER.error("Disconnected: %s", exc)
        self._active = False
        self._connected = False
        self.transport.close()
        self._msg_task.cancel()
        self.status_manager.reset()
        for queue in [self._cmdq, self._msgq]:
            while not queue.empty():
                queue.get_nowait()

    @property
    def connected(self):
        """Return the connection status"""
        return self._connected

    async def disconnect(self):
        """Disconnect gracefully."""
        if self.transport.is_closing() or not self.connected:
            return
        self._connected = False
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

    def line_received(self, line):
        """
        Gets called by data_received() when a complete line is
        received.
        Inspect the received line and process or queue accordingly.
        """
        self._received_lines += 1
        _LOGGER.debug("Received line %d: %s", self._received_lines, line)
        if self.activity_callback:
            self.loop.create_task(self.activity_callback())
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
            return None, None, None, None, None
        msgtype = self._get_msgtype(frame[0])
        if msgtype in (v.READ_ACK, v.WRITE_ACK, v.READ_DATA, v.WRITE_DATA):
            # Some info is best read from the READ/WRITE_DATA messages
            # as the boiler may not support the data ID.
            # Slice syntax is used to prevent implicit cast to int.
            data_id = frame[1:2]
            data_msb = frame[2:3]
            data_lsb = frame[3:4]
            return recvfrom, msgtype, data_id, data_msb, data_lsb
        return None, None, None, None, None

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
            part = v.THERMOSTAT
        else:  # src in "BR"
            part = v.BOILER
        update = {}

        for action in m.REGISTRY[msgid][m.MSG_TYPE[mtype]]:
            update.update(await self._get_dict_update_for_action(action, locals()))

        if update == {}:
            return

        self.status_manager.submit_partial_update(part, update)

    async def _get_dict_update_for_action(self, action, env):
        """Return a partial dict update for message"""
        func = getattr(self, action[m.FUNC])
        loc = locals()
        loc.update(env)
        args = (loc[arg] for arg in action[m.ARGS])
        if asyncio.iscoroutinefunction(func):
            ret = await func(*args)
        else:
            ret = func(*args)
        ret = ret if isinstance(ret, list) else [ret]
        update = {}
        for var, val in zip(action[m.RETURNS], ret):
            if var is False:
                return {}
            if var is None:
                continue
            update.update({var: val})
        return update

    async def _quirk_trovrd(self, part, src, msb, lsb):
        """Handle MSG_TROVRD with iSense quirk"""
        update = {}
        ovrd_value = self._get_f8_8(msb, lsb)
        if ovrd_value > 0:
            # iSense quirk: the gateway keeps sending override value
            # even if the thermostat has cancelled the override.
            if (
                self.status_manager.status[v.OTGW].get(v.OTGW_THRM_DETECT) == "I"
                and src == "A"
            ):
                ovrd = await self.issue_cmd(
                    v.OTGW_CMD_REPORT, v.OTGW_REPORT_SETPOINT_OVRD
                )
                match = re.match(r"^O=(N|[CT]([0-9]+.[0-9]+))$", ovrd, re.IGNORECASE)
                if not match:
                    return
                if match.group(1) in "Nn":
                    self.status_manager.delete_value(part, v.DATA_ROOM_SETPOINT_OVRD)
                    return
                update[v.DATA_ROOM_SETPOINT_OVRD] = float(match.group(2))
            else:
                update[v.DATA_ROOM_SETPOINT_OVRD] = ovrd_value
            self.status_manager.submit_partial_update(part, update)
        else:
            self.status_manager.delete_value(part, v.DATA_ROOM_SETPOINT_OVRD)

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

    @property
    def active(self):
        """Indicate that we have seen activity on the serial line."""
        return self._active

    async def init_and_wait_for_activity(self):
        """Wait for activity on the serial connection."""
        await self.issue_cmd(v.OTGW_CMD_SUMMARY, 0, retry=0)
        while not self.active:
            await asyncio.sleep(0)
