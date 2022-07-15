"""OpenTherm Gateway command handler."""

import asyncio
import logging
import re
from asyncio.queues import QueueFull

from pyotgw import vars as v

_LOGGER = logging.getLogger(__name__)


class CommandProcessor:
    """OpenTherm Gateway command handler."""

    def __init__(
        self,
        protocol,
        status_manager,
    ):
        """Initialise the CommandProcessor object."""
        self.protocol = protocol
        self._lock = asyncio.Lock()
        self._cmdq = asyncio.Queue()
        self.status_manager = status_manager

    async def issue_cmd(self, cmd, value, retry=3):
        """
        Issue a command, then await and return the return value.

        This method is a coroutine
        """
        async with self._lock:
            if not self.protocol.connected:
                _LOGGER.debug("Serial transport closed, not sending command %s", cmd)
                return
            self.clear_queue()
            if isinstance(value, float):
                value = f"{value:.2f}"
            _LOGGER.debug("Sending command: %s with value %s", cmd, value)
            self.protocol.transport.write(f"{cmd}={value}\r\n".encode("ascii"))
            expect = self._get_expected_response(cmd, value)

            async def send_again(err):
                """Resend the command."""
                nonlocal retry
                _LOGGER.warning("Command %s failed with %s, retrying...", cmd, err)
                retry -= 1
                self.protocol.transport.write(f"{cmd}={value}\r\n".encode("ascii"))

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

    def clear_queue(self):
        """Clear leftover messages from the command queue"""
        while not self._cmdq.empty():
            _LOGGER.debug(
                "Clearing leftover message from command queue: %s",
                self._cmdq.get_nowait(),
            )

    def submit_response(self, response):
        """Add a possible response to the command queue"""
        try:
            self._cmdq.put_nowait(response)
            _LOGGER.debug("Response submitted. Queue size: %d", self._cmdq.qsize())
        except QueueFull:
            _LOGGER.error("Queue full, discarded message: %s", response)

    @staticmethod
    def _get_expected_response(cmd, value):
        """Return the expected response pattern"""
        if cmd == v.OTGW_CMD_REPORT:
            return rf"^{cmd}:\s*([A-Z]{{2}}|{value}=[^$]+)$"
        # OTGW_CMD_CONTROL_HEATING_2 and OTGW_CMD_CONTROL_SETPOINT_2 do not adhere
        # to the standard response format (<cmd>: <value>) at the moment, but report
        # only the value. This will likely be fixed in the future, so we support
        # both formats.
        if cmd in (
            v.OTGW_CMD_CONTROL_HEATING_2,
            v.OTGW_CMD_CONTROL_SETPOINT_2,
        ):
            return rf"^(?:{cmd}:\s*)?(0|1|[0-9]+\.[0-9]{{2}}|[A-Z]{{2}})$"
        return rf"^{cmd}:\s*([^$]+)$"
