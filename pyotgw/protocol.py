"""Asyncio protocol implementation for pyotgw"""

import asyncio
import logging
import re
from asyncio.queues import QueueFull

from pyotgw import vars as v
from pyotgw.messageprocessor import MessageProcessor

_LOGGER = logging.getLogger(__name__)


class OpenThermProtocol(asyncio.Protocol):
    """
    Implementation of the Opentherm Gateway protocol to be used with
    asyncio connections.
    """

    def __init__(
        self,
        status_manager,
        activity_callback,
        loop,
    ):
        """Initialise the protocol object."""
        self.transport = None
        self.loop = loop
        self._active = False
        self._cmd_lock = asyncio.Lock()
        self._cmdq = asyncio.Queue()
        self._readbuf = b""
        self._received_lines = 0
        self.activity_callback = activity_callback
        self._connected = False
        self.message_processor = MessageProcessor(
            self,
            status_manager,
            loop,
        )
        self.status_manager = status_manager

    def connection_made(self, transport):
        """Gets called when a connection to the gateway is established."""
        self.transport = transport
        self._received_lines = 0
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
        self.message_processor.connection_lost()
        self.status_manager.reset()
        while not self._cmdq.empty():
            self._cmdq.get_nowait()

    @property
    def connected(self):
        """Return the connection status"""
        return self._connected

    async def cleanup(self):
        """Clean up"""
        self.disconnect()
        await self.message_processor.cleanup()

    def disconnect(self):
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
            self.message_processor.submit_matched_message(msg)
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
