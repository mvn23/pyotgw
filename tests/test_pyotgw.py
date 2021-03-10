import asyncio
import logging
from unittest.mock import patch

import pyotgw
import pytest
import serial
from pyotgw.vars import DEFAULT_STATUS

pytestmark = pytest.mark.asyncio


async def test_connect_success():
    """Test pyotgw.connect()"""
    pygw = pyotgw.pyotgw()
    loop = asyncio.get_running_loop()

    with patch("pyotgw.pyotgw.get_reports", return_value={}), patch(
        "pyotgw.pyotgw.get_status", return_value={},
    ), patch(
        "pyotgw.protocol.protocol.set_update_cb", return_value=None,
    ) as set_update_cb, patch(
        "pyotgw.protocol.protocol.setup_watchdog", return_value=None,
    ) as setup_watchdog, patch(
        "pyotgw.protocol.protocol._process_msgs", return_value=None,
    ) as process_msgs:
        status = await pygw.connect(loop, "loop://")

    assert status == DEFAULT_STATUS
    assert len(set_update_cb.mock_calls) == 1
    assert len(setup_watchdog.mock_calls) == 1
    assert len(process_msgs.mock_calls) == 1


async def test_connect_serialexception(caplog):
    """Test pyotgw.connect() with SerialException"""
    pygw = pyotgw.pyotgw()
    pygw._retry_timeout = 0.1
    loop = asyncio.get_running_loop()

    with patch(
        "serial_asyncio.create_serial_connection",
        return_value=(None, None),
        side_effect=serial.SerialException,
    ) as create_serial_connection:
        loop.create_task(pygw.connect(loop, "loop://"))

        await asyncio.sleep(0.5)
        assert type(pygw._attempt_connect) == asyncio.Task
        assert len(caplog.records) == 1
        assert caplog.record_tuples == [
            (
                "pyotgw.pyotgw",
                logging.ERROR,
                "Could not connect to serial device on loop://. "
                "Will keep trying. Reported error was: ",
            )
        ]
        assert len(create_serial_connection.mock_calls) > 1

    pygw._attempt_connect.cancel()
    try:
        await pygw._attempt_connect
    except asyncio.CancelledError:
        pygw._attempt_connect = None
