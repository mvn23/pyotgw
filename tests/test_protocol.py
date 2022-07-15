"""Tests for pyotgw/protocol.py"""

import asyncio
import logging
from unittest.mock import patch

import pytest

import pyotgw.vars as v
from tests.helpers import called_x_times


def test_connection_made(pygw_proto):
    """Test OpenThermProtocol.connection_made()"""
    # pygw_proto already calls connection_made()
    assert pygw_proto.connected


def test_connection_lost(caplog, pygw_proto):
    """Test OpenThermProtocol.connection_lost()"""
    pygw_proto._received_lines = 1
    pygw_proto.command_processor.submit_response("test cmdq")
    assert not pygw_proto.command_processor._cmdq.empty()

    with caplog.at_level(logging.ERROR):
        pygw_proto.connection_lost(None)

    assert not pygw_proto.active
    assert pygw_proto.command_processor._cmdq.empty()
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_line_received(caplog, pygw_proto):
    """Test OpenThermProtocol.line_received()"""
    test_lines = ("BCDEF", "A1A2B3C4D", "MustBeCommand", "AlsoCommand")

    with caplog.at_level(logging.DEBUG):
        pygw_proto.line_received(test_lines[0])

    pygw_proto.activity_callback.assert_called_once()
    assert not pygw_proto.active
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

    assert pygw_proto.active
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

    assert pygw_proto.active
    pygw_proto.activity_callback.assert_called_once()
    assert pygw_proto.command_processor._cmdq.qsize() == 1
    assert pygw_proto.command_processor._cmdq.get_nowait() == test_lines[2]
    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.DEBUG,
            f"Received line 2: {test_lines[2]}",
        ),
        (
            "pyotgw.protocol",
            logging.DEBUG,
            "Submitting line 2 to CommandProcessor",
        ),
        (
            "pyotgw.commandprocessor",
            logging.DEBUG,
            "Response submitted. Queue size: 1",
        ),
    ]

    pygw_proto.activity_callback.reset_mock()
    caplog.clear()


def test_active(pygw_proto):
    """Test OpenThermProtocol.active()"""
    pygw_proto._received_lines = 0
    assert pygw_proto.active is False
    pygw_proto._received_lines = 1
    assert pygw_proto.active is True


@pytest.mark.asyncio
async def test_init_and_wait_for_activity(pygw_proto):
    """Test OpenThermProtocol.init_and_wait_for_activity()"""
    loop = asyncio.get_running_loop()

    with patch.object(pygw_proto.command_processor, "issue_cmd") as issue_cmd:
        task = loop.create_task(pygw_proto.init_and_wait_for_activity())
        await called_x_times(issue_cmd, 1)
    pygw_proto._received_lines = 1
    await task
