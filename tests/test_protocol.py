"""Tests for pyotgw/protocol.py"""

import asyncio
import logging
from unittest.mock import MagicMock, call, patch

import pytest

import pyotgw.vars as v
from tests.helpers import called_once, called_x_times, let_queue_drain

pytestmark = pytest.mark.asyncio


def test_connection_made(pygw_proto):
    """Test OpenThermProtocol.connection_made()"""
    # pygw_proto already calls connection_made()
    assert pygw_proto.connected


def test_connection_lost(caplog, pygw_proto):
    """Test OpenThermProtocol.connection_lost()"""
    pygw_proto._active = True
    pygw_proto._cmdq.put_nowait("test cmdq")

    with caplog.at_level(logging.ERROR):
        pygw_proto.connection_lost(None)

    assert not pygw_proto.active
    assert pygw_proto._cmdq.empty()
    assert pygw_proto.status_manager.status == v.DEFAULT_STATUS
    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.ERROR,
            "Disconnected: None",
        ),
    ]


def test_connected(pygw_proto):
    """Test OpenThermProtocol.connected()"""
    assert pygw_proto.connected is True
    pygw_proto._connected = False
    assert pygw_proto.connected is False


async def test_cleanup(pygw_proto):
    """Test OpenThermProtocol.cleanup()"""
    with patch.object(
        pygw_proto.message_processor,
        "cleanup",
    ) as message_processor_cleanup:
        await pygw_proto.cleanup()
    message_processor_cleanup.assert_called_once()


def test_disconnect(pygw_proto):
    """Test OpenThermProtocol.disconnect()"""
    pygw_proto.disconnect()

    pygw_proto._connected = True
    pygw_proto.transport.is_closing.return_value = False

    pygw_proto.disconnect()

    assert not pygw_proto.connected
    pygw_proto.transport.close.assert_called_once()


def test_data_received(caplog, pygw_proto):
    """Test OpenThermProtocol.data_received()"""
    test_input = (
        b"ignorethis\x04A123",
        b"45678\r\n",
        b"\x80\r\n",
    )
    with patch.object(pygw_proto, "line_received") as line_received:
        pygw_proto.data_received(test_input[0])

        assert pygw_proto.active
        line_received.assert_not_called()

        pygw_proto.data_received(test_input[1])
        line_received.assert_called_once_with("A12345678")

        with caplog.at_level(logging.DEBUG):
            pygw_proto.data_received(test_input[2])
        assert pygw_proto._readbuf == b""
        assert caplog.record_tuples == [
            (
                "pyotgw.protocol",
                logging.DEBUG,
                "Invalid data received, ignoring...",
            ),
        ]


def test_line_received(caplog, pygw_proto):
    """Test OpenThermProtocol.line_received()"""
    test_lines = ("BCDEF", "A1A2B3C4D", "MustBeCommand", "AlsoCommand")

    with caplog.at_level(logging.DEBUG):
        pygw_proto.line_received(test_lines[0])

    pygw_proto.activity_callback.assert_called_once()
    assert pygw_proto._received_lines == 0
    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.DEBUG,
            f"Received line 1: {test_lines[0]}",
        ),
        (
            "pyotgw.protocol",
            logging.DEBUG,
            f"Ignoring line: {test_lines[0]}",
        ),
    ]

    pygw_proto.activity_callback.reset_mock()
    caplog.clear()

    with patch.object(
        pygw_proto.message_processor,
        "submit_matched_message",
    ) as submit_message, caplog.at_level(logging.DEBUG):
        pygw_proto.line_received(test_lines[1])

    assert pygw_proto._received_lines == 1
    pygw_proto.activity_callback.assert_called_once()
    submit_message.assert_called_once()
    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.DEBUG,
            f"Received line 1: {test_lines[1]}",
        ),
    ]

    pygw_proto.activity_callback.reset_mock()
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        pygw_proto.line_received(test_lines[2])

    assert pygw_proto._received_lines == 2
    pygw_proto.activity_callback.assert_called_once()
    assert pygw_proto._cmdq.qsize() == 1
    assert pygw_proto._cmdq.get_nowait() == test_lines[2]
    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.DEBUG,
            f"Received line 2: {test_lines[2]}",
        ),
        (
            "pyotgw.protocol",
            logging.DEBUG,
            "Added line 2 to command queue. Queue size: 1",
        ),
    ]

    pygw_proto.activity_callback.reset_mock()
    caplog.clear()

    with patch.object(
        pygw_proto._cmdq, "put_nowait", side_effect=asyncio.QueueFull
    ) as put_nowait, caplog.at_level(logging.ERROR):
        pygw_proto.line_received(test_lines[3])

    pygw_proto.activity_callback.assert_called_once()
    put_nowait.assert_called_once_with(test_lines[3])
    assert pygw_proto._cmdq.qsize() == 0
    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.ERROR,
            f"Queue full, discarded message: {test_lines[3]}",
        ),
    ]


async def test_issue_cmd(caplog, pygw_proto):
    """Test OpenThermProtocol.issue_cmd()"""
    pygw_proto._connected = False
    with caplog.at_level(logging.DEBUG):
        assert await pygw_proto.issue_cmd("PS", 1, 0) is None

    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.DEBUG,
            "Serial transport closed, not sending command PS",
        ),
    ]
    caplog.clear()

    loop = asyncio.get_running_loop()
    pygw_proto._connected = True
    pygw_proto._cmdq.put_nowait("thisshouldbecleared")
    pygw_proto.transport.write = MagicMock()

    with caplog.at_level(logging.DEBUG):
        task = loop.create_task(pygw_proto.issue_cmd(v.OTGW_CMD_REPORT, "I", 1))
        await let_queue_drain(pygw_proto._cmdq)

        pygw_proto.transport.write.assert_called_once_with(b"PR=I\r\n")
        assert caplog.record_tuples == [
            (
                "pyotgw.protocol",
                logging.DEBUG,
                "Clearing leftover message from command queue: thisshouldbecleared",
            ),
            (
                "pyotgw.protocol",
                logging.DEBUG,
                "Sending command: PR with value I",
            ),
        ]
        caplog.clear()

        pygw_proto._cmdq.put_nowait("SE")
        pygw_proto._cmdq.put_nowait("SE")
        with pytest.raises(SyntaxError):
            await task

    assert pygw_proto.transport.write.call_args_list == [
        call(b"PR=I\r\n"),
        call(b"PR=I\r\n"),
    ]

    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.DEBUG,
            "Got possible response for command PR: SE",
        ),
        (
            "pyotgw.protocol",
            logging.WARNING,
            "Command PR failed with SE, retrying...",
        ),
        (
            "pyotgw.protocol",
            logging.DEBUG,
            "Got possible response for command PR: SE",
        ),
    ]
    caplog.clear()

    pygw_proto.transport.write = MagicMock()
    with caplog.at_level(logging.WARNING):
        task = loop.create_task(
            pygw_proto.issue_cmd(v.OTGW_CMD_CONTROL_SETPOINT_2, 20.501, 1)
        )
        await called_once(pygw_proto.transport.write)
        pygw_proto.transport.write.assert_called_once_with(b"C2=20.50\r\n")
        pygw_proto._cmdq.put_nowait("InvalidCommand")
        pygw_proto._cmdq.put_nowait("C2: 20.50")
        assert await task == "20.50"

    assert pygw_proto.transport.write.call_args_list == [
        call(b"C2=20.50\r\n"),
        call(b"C2=20.50\r\n"),
    ]
    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.WARNING,
            "Unknown message in command queue: InvalidCommand",
        ),
        (
            "pyotgw.protocol",
            logging.WARNING,
            "Command C2 failed with InvalidCommand, retrying...",
        ),
    ]
    caplog.clear()

    pygw_proto.transport.write = MagicMock()
    with caplog.at_level(logging.WARNING):
        task = loop.create_task(
            pygw_proto.issue_cmd(v.OTGW_CMD_CONTROL_HEATING_2, -1, 2)
        )
        await called_once(pygw_proto.transport.write)
        pygw_proto.transport.write.assert_called_once_with(b"H2=-1\r\n")
        pygw_proto._cmdq.put_nowait("Error 03")
        pygw_proto._cmdq.put_nowait("H2: BV")
        pygw_proto._cmdq.put_nowait("H2: BV")
        with pytest.raises(ValueError):
            await task

    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.WARNING,
            "Received Error 03. "
            "If this happens during a reset of the gateway it can be safely ignored.",
        ),
        (
            "pyotgw.protocol",
            logging.WARNING,
            "Command H2 failed with Error 03, retrying...",
        ),
        (
            "pyotgw.protocol",
            logging.WARNING,
            "Command H2 failed with H2: BV, retrying...",
        ),
    ]

    pygw_proto.transport.write = MagicMock()
    task = loop.create_task(pygw_proto.issue_cmd(v.OTGW_CMD_MODE, "R", 0))
    await called_once(pygw_proto.transport.write)
    pygw_proto._cmdq.put_nowait("ThisGetsIgnored")
    pygw_proto._cmdq.put_nowait("OpenTherm Gateway 4.3.5")

    assert await task is True

    pygw_proto.transport.write = MagicMock()
    task = loop.create_task(pygw_proto.issue_cmd(v.OTGW_CMD_SUMMARY, 1, 0))
    await called_once(pygw_proto.transport.write)
    pygw_proto._cmdq.put_nowait("PS: 1")
    pygw_proto._cmdq.put_nowait("part_2_will_normally_be_parsed_by_get_status")

    assert await task == ["1", "part_2_will_normally_be_parsed_by_get_status"]


def test_active(pygw_proto):
    """Test OpenThermProtocol.active()"""
    pygw_proto._active = False
    assert pygw_proto.active is False
    pygw_proto._active = True
    assert pygw_proto.active is True


async def test_init_and_wait_for_activity(pygw_proto):
    """Test OpenThermProtocol.init_and_wait_for_activity()"""
    loop = asyncio.get_running_loop()

    with patch.object(pygw_proto, "issue_cmd") as issue_cmd:
        task = loop.create_task(pygw_proto.init_and_wait_for_activity())
        await called_x_times(issue_cmd, 1)
    pygw_proto._active = True
    await task
