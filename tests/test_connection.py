"""Tests for pyotgw/connection.py"""

import asyncio
import functools
import logging
from unittest.mock import DEFAULT, MagicMock, patch

import pytest
import serial

from pyotgw.connection import MAX_RETRY_TIMEOUT
from pyotgw.protocol import OpenThermProtocol
from tests.helpers import called_once, called_x_times


@pytest.mark.asyncio
async def test_connect_success_and_reconnect(caplog, pygw_conn, pygw_proto):
    """Test ConnectionManager.connect()"""
    pygw_conn._error = asyncio.CancelledError()

    with patch.object(
        pygw_conn,
        "_attempt_connect",
        return_value=(pygw_proto.transport, pygw_proto),
    ) as attempt_connect, caplog.at_level(logging.DEBUG):
        assert await pygw_conn.connect("loop://")

    assert pygw_conn._port == "loop://"
    attempt_connect.assert_called_once()
    assert pygw_conn._connecting_task is None
    assert pygw_conn._error is None
    assert caplog.record_tuples == [
        (
            "pyotgw.connection",
            logging.DEBUG,
            "Connected to serial device on loop://",
        ),
    ]
    assert pygw_conn._transport == pygw_proto.transport
    assert pygw_conn.protocol == pygw_proto
    assert pygw_conn.watchdog.is_active
    assert pygw_conn.connected

    await pygw_conn.watchdog.stop()
    caplog.clear()

    with patch.object(
        pygw_conn,
        "_attempt_connect",
        return_value=(pygw_proto.transport, pygw_proto),
    ) as attempt_connect, caplog.at_level(logging.DEBUG):
        assert await pygw_conn.connect("loop://new")

    assert pygw_conn._port == "loop://new"
    attempt_connect.assert_called_once()
    assert pygw_conn._connecting_task is None
    assert pygw_conn._error is None
    assert caplog.record_tuples == [
        (
            "pyotgw.connection",
            logging.DEBUG,
            "Reconnecting to serial device on loop://new",
        ),
        (
            "pyotgw.connection",
            logging.DEBUG,
            "Connected to serial device on loop://new",
        ),
    ]
    assert pygw_conn._transport == pygw_proto.transport
    assert pygw_conn.protocol == pygw_proto
    assert pygw_conn.watchdog.is_active
    assert pygw_conn.connected


@pytest.mark.asyncio
async def test_connect_cancel(pygw_conn):
    """Test ConnectionManager.connect() cancellation"""
    with patch.object(
        pygw_conn,
        "_attempt_connect",
        side_effect=asyncio.CancelledError,
    ) as create_serial_connection:
        assert not await pygw_conn.connect("loop://")

    create_serial_connection.assert_called_once()


@pytest.mark.asyncio
async def test_disconnect(pygw_conn, pygw_proto):
    """Test ConnectionManager.disconnect()"""
    with patch.object(
        pygw_conn,
        "_attempt_connect",
        return_value=(pygw_proto.transport, pygw_proto),
    ):
        assert await pygw_conn.connect("loop://")

    with patch.object(
        pygw_proto,
        "disconnect",
    ) as disconnect:
        await pygw_conn.disconnect()
    assert disconnect.called


@pytest.mark.asyncio
async def test_disconnect_while_connecting(pygw_conn):
    """Test ConnectionManager.disconnect() during an ongoing connection attempt"""
    loop = asyncio.get_running_loop()

    async def wait_forever():
        while True:
            await asyncio.sleep(1)

    with patch.object(
        pygw_conn,
        "_attempt_connect",
        side_effect=wait_forever,
    ) as attempt_connect:
        task = loop.create_task(pygw_conn.connect("loop://"))
        await called_once(attempt_connect)
        await pygw_conn.disconnect()

        assert await task is False
        assert not pygw_conn.connected


@pytest.mark.asyncio
async def test_reconnect(caplog, pygw_conn):
    """Test ConnectionManager.reconnect()"""
    with patch.object(pygw_conn, "disconnect") as disconnect, patch.object(
        pygw_conn,
        "connect",
    ) as connect, caplog.at_level(logging.ERROR):
        await pygw_conn.reconnect()

    disconnect.assert_not_called()
    connect.assert_not_called()
    assert caplog.record_tuples == [
        ("pyotgw.connection", logging.ERROR, "Reconnect called before connect!")
    ]

    caplog.clear()
    pygw_conn._port = "loop://"
    with patch.object(pygw_conn, "disconnect") as disconnect, patch.object(
        pygw_conn,
        "connect",
    ) as connect, caplog.at_level(logging.DEBUG):
        await pygw_conn.reconnect()

    assert caplog.record_tuples == [
        ("pyotgw.connection", logging.DEBUG, "Scheduling reconnect...")
    ]
    disconnect.assert_called_once()
    connect.assert_called_once_with("loop://")


@pytest.mark.asyncio
async def test_reconnect_after_connection_loss(caplog, pygw_conn, pygw_proto):
    """Test ConnectionManager.reconnect() after connection loss"""
    pygw_conn._error = asyncio.CancelledError()

    with patch.object(
        pygw_conn,
        "_attempt_connect",
        return_value=(pygw_proto.transport, pygw_proto),
    ) as attempt_conn, patch.object(
        pygw_conn.watchdog,
        "start",
        side_effect=pygw_conn.watchdog.start,
    ) as wd_start, caplog.at_level(
        logging.DEBUG
    ):
        assert await pygw_conn.connect("loop://", timeout=0.001)

        caplog.clear()
        attempt_conn.assert_called_once()
        attempt_conn.reset_mock()
        await called_x_times(wd_start, 2, timeout=3)
        attempt_conn.assert_called_once()
        assert caplog.record_tuples == [
            (
                "pyotgw.connection",
                logging.DEBUG,
                "Watchdog triggered!",
            ),
            (
                "pyotgw.connection",
                logging.DEBUG,
                "Canceling Watchdog task.",
            ),
            (
                "pyotgw.connection",
                logging.DEBUG,
                "Scheduling reconnect...",
            ),
            (
                "pyotgw.connection",
                logging.DEBUG,
                "Reconnecting to serial device on loop://",
            ),
            (
                "pyotgw.connection",
                logging.DEBUG,
                "Connected to serial device on loop://",
            ),
        ]


def test_connected(pygw_conn, pygw_proto):
    """Test ConnectionManager.connected()"""
    pygw_conn.protocol = pygw_proto
    pygw_conn.protocol._connected = False
    assert not pygw_conn.connected
    pygw_conn.protocol._connected = True
    assert pygw_conn.connected


def test_set_connection_config(pygw_conn):
    """Test ConnectionManager.set_connection_config()"""
    assert pygw_conn.set_connection_config(baudrate=19200, parity=serial.PARITY_NONE)
    assert pygw_conn._config == {
        "baudrate": 19200,
        "bytesize": serial.EIGHTBITS,
        "parity": serial.PARITY_NONE,
        "stopbits": serial.STOPBITS_ONE,
    }

    assert not pygw_conn.set_connection_config(baudrate=9600, invalid="value")
    assert pygw_conn._config == {
        "baudrate": 19200,
        "bytesize": serial.EIGHTBITS,
        "parity": serial.PARITY_NONE,
        "stopbits": serial.STOPBITS_ONE,
    }

    with patch("pyotgw.connection.ConnectionManager.connected", return_value=True):
        assert not pygw_conn.set_connection_config()


@pytest.mark.asyncio
async def test_attempt_connect_success(pygw_conn, pygw_proto):
    """Test ConnectionManager._attempt_connect()"""
    pygw_conn._port = "loop://"

    # We cannot compare the functools.partial object which is created in-line
    # so we have to manually save args and kwargs and compare them one by one.
    saved_args_list = []

    def save_args(*used_args, **used_kwargs):
        """Store args and kwargs each time we're called"""
        saved_args_list.append({"args": used_args, "kwargs": used_kwargs})
        return DEFAULT

    with patch(
        "pyotgw.protocol.OpenThermProtocol.init_and_wait_for_activity",
    ) as init_and_wait, patch(
        "serial_asyncio.create_serial_connection",
        return_value=(pygw_proto.transport, pygw_proto),
        side_effect=save_args,
    ) as create_serial_connection:
        assert await pygw_conn._attempt_connect() == (pygw_proto.transport, pygw_proto)

    create_serial_connection.assert_called_once()
    assert len(saved_args_list) == 1
    args = saved_args_list[0]["args"]
    assert len(args) == 3
    assert args[0] == asyncio.get_running_loop()
    assert isinstance(args[1], functools.partial)
    assert args[1].func == OpenThermProtocol
    assert args[1].args == (
        pygw_conn.status_manager,
        pygw_conn.watchdog.inform,
    )
    assert args[2] == pygw_conn._port
    kwargs = saved_args_list[0]["kwargs"]
    assert kwargs == {
        "write_timeout": 0,
        "baudrate": 9600,
        "bytesize": serial.EIGHTBITS,
        "parity": serial.PARITY_NONE,
        "stopbits": serial.STOPBITS_ONE,
    }
    init_and_wait.assert_called_once()


@pytest.mark.asyncio
async def test_attempt_connect_serialexception(caplog, pygw_conn):
    """Test ConnectionManager._attempt_connect() with SerialException"""
    loop = asyncio.get_running_loop()
    pygw_conn._port = "loop://"

    with patch(
        "serial_asyncio.create_serial_connection",
        side_effect=serial.SerialException,
    ) as create_serial_connection, patch.object(
        pygw_conn,
        "_get_retry_timeout",
        return_value=0,
    ) as retry_timeout, caplog.at_level(
        logging.ERROR
    ):
        task = loop.create_task(pygw_conn._attempt_connect())
        await called_x_times(retry_timeout, 2)

        assert create_serial_connection.call_count >= 2
        assert caplog.record_tuples == [
            (
                "pyotgw.connection",
                logging.ERROR,
                "Could not connect to serial device on loop://. "
                "Will keep trying. Reported error was: ",
            )
        ]

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_attempt_connect_timeouterror(caplog, pygw_conn, pygw_proto):
    """Test ConnectionManager._attempt_connect() with SerialException"""
    loop = asyncio.get_running_loop()
    pygw_conn._port = "loop://"

    pygw_proto.init_and_wait_for_activity = MagicMock(side_effect=asyncio.TimeoutError)
    pygw_proto.disconnect = MagicMock()

    with patch(
        "serial_asyncio.create_serial_connection",
        return_value=(pygw_proto.transport, pygw_proto),
    ) as create_serial_connection, patch.object(
        pygw_conn,
        "_get_retry_timeout",
        return_value=0,
    ) as retry_timeout, caplog.at_level(
        logging.ERROR
    ):
        task = loop.create_task(pygw_conn._attempt_connect())
        await called_x_times(retry_timeout, 2)

        assert create_serial_connection.call_count >= 2
        assert pygw_proto.disconnect.call_count >= 2
        assert caplog.record_tuples == [
            (
                "pyotgw.connection",
                logging.ERROR,
                "The serial device on loop:// is not responding. " "Will keep trying.",
            )
        ]

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_cleanup(pygw_conn):
    """Test ConnectionManager._cleanup()"""
    pass  # with patch.object()


def test_get_retry_timeout(pygw):
    """Test pyotgw._get_retry_timeout()"""
    pygw.connection._retry_timeout = MAX_RETRY_TIMEOUT / 2
    assert pygw.connection._get_retry_timeout() == MAX_RETRY_TIMEOUT / 2
    assert pygw.connection._get_retry_timeout() == (MAX_RETRY_TIMEOUT / 2) * 1.5
    assert pygw.connection._get_retry_timeout() == MAX_RETRY_TIMEOUT


def test_is_active(pygw_watchdog):
    """Test ConnectionWatchdog.is_active()"""
    assert not pygw_watchdog.is_active
    pygw_watchdog.start(None, 10)
    assert pygw_watchdog.is_active


@pytest.mark.asyncio
async def test_inform_watchdog(caplog, pygw_watchdog):
    """Test ConnectionWatchdog.inform()"""
    await pygw_watchdog.inform()

    async def empty_coroutine():
        return

    pygw_watchdog.start(empty_coroutine, 10)

    with patch.object(
        pygw_watchdog._wd_task,
        "cancel",
        side_effect=pygw_watchdog._wd_task.cancel,
    ) as task_cancel, patch.object(
        pygw_watchdog,
        "_watchdog",
    ) as watchdog, caplog.at_level(
        logging.DEBUG
    ):
        await pygw_watchdog.inform()

    task_cancel.assert_called_once()
    watchdog.assert_called_once_with(pygw_watchdog.timeout)
    assert caplog.record_tuples == [
        ("pyotgw.connection", logging.DEBUG, "Watchdog timer reset!")
    ]


def test_start(pygw_watchdog):
    """Test ConnectionWatchdog.start()"""

    def callback():
        return

    with patch.object(
        pygw_watchdog,
        "_watchdog",
    ) as watchdog:
        assert pygw_watchdog.start(callback, 10)

    assert pygw_watchdog.timeout == 10
    assert pygw_watchdog._callback == callback
    watchdog.assert_called_once_with(10)

    assert not pygw_watchdog.start(callback, 10)


@pytest.mark.asyncio
async def test_stop(caplog, pygw_watchdog):
    """Test ConnectionWatchdog.stop()"""
    with caplog.at_level(logging.DEBUG):
        await pygw_watchdog.stop()

    assert caplog.records == []

    async def empty_coroutine():
        return

    pygw_watchdog.start(empty_coroutine, 10)
    with caplog.at_level(logging.DEBUG):
        await pygw_watchdog.stop()

    assert not pygw_watchdog.is_active
    assert caplog.record_tuples == [
        (
            "pyotgw.connection",
            logging.DEBUG,
            "Canceling Watchdog task.",
        ),
    ]


@pytest.mark.asyncio
async def test_watchdog(caplog, pygw_watchdog):
    """Test ConnectionWatchdog._watchdog()"""

    async def empty_callback():
        return

    watchdog_callback = MagicMock(side_effect=empty_callback)
    pygw_watchdog.start(watchdog_callback, 0)

    with caplog.at_level(logging.DEBUG):
        await called_once(watchdog_callback)

    assert caplog.record_tuples == [
        (
            "pyotgw.connection",
            logging.DEBUG,
            "Watchdog triggered!",
        ),
        (
            "pyotgw.connection",
            logging.DEBUG,
            "Canceling Watchdog task.",
        ),
    ]
