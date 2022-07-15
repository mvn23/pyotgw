"""Asyncio protocol implementation for pyotgw"""

import asyncio
import logging
import re

from pyotgw import vars as v
from pyotgw.commandprocessor import CommandProcessor
from pyotgw.messageprocessor import MessageProcessor

_LOGGER = logging.getLogger(__name__)


class OpenThermProtocol(
    asyncio.Protocol
):  # pylint: disable=too-many-instance-attributes
    """
    Implementation of the Opentherm Gateway protocol to be used with
    asyncio connections.
    """

    def __init__(
        self,
        status_manager,
        activity_callback,
    ):
        """Initialise the protocol object."""
        self.transport = None
        self._readbuf = b""
        self._received_lines = 0
        self.activity_callback = activity_callback
        self.command_processor = CommandProcessor(
            self,
            status_manager,
        )
        self._connected = False
        self.message_processor = MessageProcessor(
            self.command_processor,
            status_manager,
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
        self._received_lines = 0
        self._connected = False
        self.command_processor.clear_queue()
        self.message_processor.connection_lost()
        self.status_manager.reset()

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
            asyncio.create_task(self.activity_callback())
        pattern = r"^(T|B|R|A|E)([0-9A-F]{8})$"
        msg = re.match(pattern, line)
        if msg:
            self.message_processor.submit_matched_message(msg)
        elif re.match(r"^[0-9A-F]{1,8}$", line) and self._received_lines == 1:
            # Partial message on fresh connection. Ignore.
            self._received_lines = 0
            _LOGGER.debug("Ignoring line: %s", line)
        else:
            _LOGGER.debug(
                "Submitting line %d to CommandProcessor",
                self._received_lines,
            )
            self.command_processor.submit_response(line)

    @property
    def active(self):
        """Indicate that we have seen activity on the serial line."""
        return self._received_lines > 0

    async def init_and_wait_for_activity(self):
        """Wait for activity on the serial connection."""
        await self.command_processor.issue_cmd(v.OTGW_CMD_SUMMARY, 0, retry=0)
        while not self.active:
            await asyncio.sleep(0)
