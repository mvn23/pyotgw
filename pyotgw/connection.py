"""
Connection Manager for pyotgw.
Everything related to making, maintaining and monitoring the connection
to the gateway goes here.
"""

import asyncio
import logging
from functools import partial

import serial
import serial_asyncio

from pyotgw.protocol import OpenThermProtocol

CONNECTION_TIMEOUT = 5

MAX_RETRY_TIMEOUT = 60
MIN_RETRY_TIMEOUT = 5

WATCHDOG_TIMEOUT = 3

_LOGGER = logging.getLogger(__name__)


class ConnectionManager:  # pylint: disable=too-many-instance-attributes
    """Functionality for setting up and tearing down a connection"""

    def __init__(self, status_manager):
        """Initialise the connection manager"""
        self._error = None
        self._port = None
        self._retry_timeout = MIN_RETRY_TIMEOUT
        self._connecting_task = None
        self._config = {
            "baudrate": 9600,
            "bytesize": serial.EIGHTBITS,
            "parity": serial.PARITY_NONE,
            "stopbits": serial.STOPBITS_ONE,
        }
        self.status_manager = status_manager
        self.watchdog = ConnectionWatchdog()
        self._transport = None
        self.protocol = None

    async def connect(self, port, timeout=None):
        """Start connection attempts. Return True on success or False on failure."""
        if self.connected or self._connecting_task:
            # We are actually reconnecting, cleanup first.
            _LOGGER.debug("Reconnecting to serial device on %s", port)
            await self.disconnect()

        loop = asyncio.get_running_loop()
        self._port = port
        self._connecting_task = loop.create_task(self._attempt_connect())
        try:
            transport, protocol = await self._connecting_task
        except asyncio.CancelledError:
            return False
        finally:
            self._connecting_task = None
        self._error = None
        _LOGGER.debug("Connected to serial device on %s", port)
        self._transport = transport
        self.protocol = protocol
        self.watchdog.start(self.reconnect, timeout=timeout or WATCHDOG_TIMEOUT)
        return True

    async def disconnect(self):
        """Disconnect from the OpenTherm Gateway."""
        await self._cleanup()
        if self.connected:
            self.protocol.disconnect()

    async def reconnect(self):
        """Reconnect to the OpenTherm Gateway."""
        if not self._port:
            _LOGGER.error("Reconnect called before connect!")
            return
        _LOGGER.debug("Scheduling reconnect...")
        await self.disconnect()
        await self.connect(self._port)

    @property
    def connected(self):
        """Return the connection status"""
        return self.protocol and self.protocol.connected

    def set_connection_config(self, **kwargs):
        """
        Set the serial connection parameters before calling connect()
        Valid kwargs are 'baudrate', 'bytesize', 'parity' and 'stopbits'.
        Returns True on success, False on fail or if already connected.
        For more information see the pyserial documentation.
        """
        if self.connected:
            return False
        for arg in kwargs:
            if arg not in self._config:
                _LOGGER.error("Invalid connection parameter: %s", arg)
                return False
        self._config.update(kwargs)
        return True

    async def _attempt_connect(self):
        """Try to connect to the OpenTherm Gateway."""
        loop = asyncio.get_running_loop()
        transport = None
        protocol = None
        self._retry_timeout = MIN_RETRY_TIMEOUT
        while transport is None:
            try:
                transport, protocol = await serial_asyncio.create_serial_connection(
                    loop,
                    partial(
                        OpenThermProtocol,
                        self.status_manager,
                        self.watchdog.inform,
                    ),
                    self._port,
                    write_timeout=0,
                    **self._config,
                )
                await asyncio.wait_for(
                    protocol.init_and_wait_for_activity(),
                    CONNECTION_TIMEOUT,
                )
                return transport, protocol

            except serial.SerialException as err:
                if not isinstance(err, type(self._error)):
                    _LOGGER.error(
                        "Could not connect to serial device on %s. "
                        "Will keep trying. Reported error was: %s",
                        self._port,
                        err,
                    )
                    self._error = err

            except asyncio.TimeoutError as err:
                if not isinstance(err, type(self._error)):
                    _LOGGER.error(
                        "The serial device on %s is not responding. "
                        "Will keep trying.",
                        self._port,
                    )
                    self._error = err
                if protocol:
                    protocol.disconnect()

            transport = None
            await asyncio.sleep(self._get_retry_timeout())

    async def _cleanup(self):
        """Cleanup possible leftovers from old connections"""
        await self.watchdog.stop()
        if self.protocol:
            await self.protocol.cleanup()
        if self._connecting_task is not None:
            self._connecting_task.cancel()
            try:
                await self._connecting_task
            except asyncio.CancelledError:
                self._connecting_task = None

    def _get_retry_timeout(self):
        """Increase if needed and return the retry timeout."""
        if self._retry_timeout == MAX_RETRY_TIMEOUT:
            return self._retry_timeout
        timeout = self._retry_timeout
        self._retry_timeout = min([self._retry_timeout * 1.5, MAX_RETRY_TIMEOUT])
        return timeout


class ConnectionWatchdog:
    """Connection watchdog"""

    def __init__(self):
        """Initialise the object"""
        self._callback = None
        self.timeout = WATCHDOG_TIMEOUT
        self._wd_task = None
        self._lock = asyncio.Lock()
        self.loop = asyncio.get_event_loop()

    @property
    def is_active(self):
        """Return watchdog status"""
        return self._wd_task is not None

    async def inform(self):
        """Reset the watchdog timer."""
        async with self._lock:
            if not self.is_active:
                # Check within the Lock to deal with external stop()
                # calls with queued inform() tasks.
                return
            self._wd_task.cancel()
            try:
                await self._wd_task
            except asyncio.CancelledError:
                self._wd_task = self.loop.create_task(self._watchdog(self.timeout))
                _LOGGER.debug("Watchdog timer reset!")

    def start(self, callback, timeout):
        """Start the watchdog, return boolean indicating success"""
        if self.is_active:
            return False
        self._callback = callback
        self.timeout = timeout
        self._wd_task = self.loop.create_task(self._watchdog(timeout))
        return self.is_active

    async def stop(self):
        """Stop the watchdog"""
        async with self._lock:
            if not self.is_active:
                return
            _LOGGER.debug("Canceling Watchdog task.")
            self._wd_task.cancel()
            try:
                await self._wd_task
            except asyncio.CancelledError:
                self._wd_task = None

    async def _watchdog(self, timeout):
        """Trigger and cancel the watchdog after timeout. Schedule callback."""
        await asyncio.sleep(timeout)
        _LOGGER.debug("Watchdog triggered!")
        self.loop.create_task(self._callback())
        await self.stop()
