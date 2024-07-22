"""OpenTherm Protocol message handler"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING

from . import messages as m
from . import vars as v

if TYPE_CHECKING:
    from .commandprocessor import CommandProcessor
    from .status import StatusManager

_LOGGER = logging.getLogger(__name__)


class MessageProcessor:
    """
    Process protocol messages and submit status updates.
    """

    def __init__(
        self,
        command_processor: CommandProcessor,
        status_manager: StatusManager,
    ) -> None:
        """Initialise the protocol object."""
        self._msgq = asyncio.Queue()
        self._task = asyncio.get_running_loop().create_task(self._process_msgs())
        self.command_processor = command_processor
        self.status_manager = status_manager

    async def cleanup(self) -> None:
        """Empty the message queue and clean up running task."""
        self.connection_lost()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                self._task = None

    def connection_lost(self) -> None:
        """
        Gets called when the connection to the gateway is lost.
        Tear down and clean up the object.
        """
        while not self._msgq.empty():
            self._msgq.get_nowait()

    def submit_matched_message(self, match: re.match) -> None:
        """Add a matched message to the processing queue."""
        src, mtype, mid, msb, lsb = self._dissect_msg(match)
        if lsb is not None:
            self._msgq.put_nowait((src, mtype, mid, msb, lsb))
            _LOGGER.debug(
                "Added line to message queue. Queue size: %d",
                self._msgq.qsize(),
            )

    def _dissect_msg(
        self, match: re.match
    ) -> tuple[str, int, bytes, bytes, bytes] | tuple[None, None, None, None, None]:
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
    def _get_msgtype(byte: bytes) -> int:
        """
        Return the message type of Opentherm messages according to
        byte.
        """
        return (byte >> 4) & 0x7

    async def _process_msgs(self) -> None:
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

    async def _process_msg(self, message: tuple[str, int, bytes, bytes, bytes]) -> None:
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

        if not update:
            return

        self.status_manager.submit_partial_update(part, update)

    async def _get_dict_update_for_action(self, action: dict, env: dict) -> dict:
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

    async def _quirk_trovrd(self, part: str, src: str, msb: bytes, lsb: bytes) -> None:
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
                ovrd = await self.command_processor.issue_cmd(
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

    async def _quirk_trset_s2m(self, part: str, msb: bytes, lsb: bytes) -> None:
        """Handle MSG_TRSET with gateway quirk"""
        # Ignore s2m messages on thermostat side as they are ALWAYS WriteAcks
        # but may contain invalid data.
        if part == v.THERMOSTAT:
            return

        self.status_manager.submit_partial_update(
            part, {v.DATA_ROOM_SETPOINT: self._get_f8_8(msb, lsb)}
        )

    @staticmethod
    def _get_flag8(byte: bytes) -> list[int]:
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
    def _get_u8(byte: bytes) -> int:
        """
        Convert a byte into an unsigned int.
        """
        return int.from_bytes(byte, "big", signed=False)

    @staticmethod
    def _get_s8(byte: bytes) -> int:
        """
        Convert a byte into a signed int.
        """
        return int.from_bytes(byte, "big", signed=True)

    def _get_f8_8(self, msb: bytes, lsb: bytes) -> float:
        """
        Convert 2 bytes into an OpenTherm f8_8 (float) value.
        """
        return float(self._get_s16(msb, lsb) / 256)

    def _get_u16(self, msb: bytes, lsb: bytes) -> int:
        """
        Convert 2 bytes into an unsigned int.
        """
        return (self._get_u8(msb) << 8) | self._get_u8(lsb)

    def _get_s16(self, msb: bytes, lsb: bytes) -> int:
        """
        Convert 2 bytes into a signed int.
        """
        return (self._get_s8(msb) << 8) | self._get_u8(lsb)
