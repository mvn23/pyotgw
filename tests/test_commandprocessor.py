"""Tests for pyotgw/commandprocessor.py"""

import asyncio
import logging
from unittest.mock import MagicMock, patch

import pytest

import pyotgw.vars as v
from tests.helpers import called_once, called_x_times, let_queue_drain


@pytest.mark.asyncio
async def test_submit_response_queuefull(caplog, pygw_proto):
    """Test queuefull on submit_response()"""
    test_line = "DoesntMatterQueueFullAnyway"
    with (
        patch.object(
            pygw_proto.command_processor._cmdq,
            "put_nowait",
            side_effect=asyncio.QueueFull,
        ) as put_nowait,
        caplog.at_level(logging.ERROR),
    ):
        pygw_proto.line_received(test_line)

    pygw_proto.activity_callback.assert_called_once()
    put_nowait.assert_called_once_with(test_line)
    assert pygw_proto.command_processor._cmdq.qsize() == 0
    assert caplog.record_tuples == [
        (
            "pyotgw.commandprocessor",
            logging.ERROR,
            f"Queue full, discarded message: {test_line}",
        ),
    ]


@pytest.mark.asyncio
async def test_issue_cmd_serial_transport_closed(caplog, pygw_proto):
    """Test OpenThermProtocol.issue_cmd() when the serial transport is closed."""
    pygw_proto._connected = False
    with caplog.at_level(logging.DEBUG):
        assert await pygw_proto.command_processor.issue_cmd("PS", 1, 0) is None

    assert caplog.record_tuples == [
        (
            "pyotgw.commandprocessor",
            logging.DEBUG,
            "Serial transport closed, not sending command PS",
        ),
    ]


@pytest.mark.asyncio
async def test_issue_cmd_leftover_cmdq_messages(caplog, pygw_proto):
    """Test OpenThermProtocol.issue_cmd() with leftover messages in command queue."""
    loop = asyncio.get_running_loop()
    pygw_proto.command_processor._cmdq.put_nowait("thisshouldbecleared")
    pygw_proto.transport.write = MagicMock()

    with caplog.at_level(logging.DEBUG):
        task = loop.create_task(
            pygw_proto.command_processor.issue_cmd(
                v.OTGW_CMD_REPORT,
                "I",
                1,
            )
        )
        await let_queue_drain(pygw_proto.command_processor._cmdq)

        pygw_proto.transport.write.assert_called_once_with(b"PR=I\r\n")
        pygw_proto.command_processor.submit_response("PR: I=00")
        assert await task == "I=00"
        assert caplog.record_tuples == [
            (
                "pyotgw.commandprocessor",
                logging.DEBUG,
                "Clearing leftover message from command queue: thisshouldbecleared",
            ),
            (
                "pyotgw.commandprocessor",
                logging.DEBUG,
                "Sending command: PR with value I",
            ),
            (
                "pyotgw.commandprocessor",
                logging.DEBUG,
                "Response submitted. Queue size: 1",
            ),
            (
                "pyotgw.commandprocessor",
                logging.DEBUG,
                "Got possible response for command PR: PR: I=00",
            ),
        ]


@pytest.mark.asyncio
async def test_issue_cmd_syntaxerror(caplog, pygw_proto):
    """Test issue_cmd SyntaxError handling."""
    loop = asyncio.get_running_loop()
    pygw_proto.transport.write = MagicMock()

    with caplog.at_level(logging.DEBUG):
        task = loop.create_task(
            pygw_proto.command_processor.issue_cmd(
                v.OTGW_CMD_REPORT,
                "I",
                1,
            )
        )

        # Wait for the command to be sent
        await called_once(pygw_proto.transport.write)

        pygw_proto.transport.write.assert_called_once_with(b"PR=I\r\n")
        pygw_proto.transport.write.reset_mock()
        pygw_proto.command_processor.submit_response("SE")

        # Wait for the command to be re-sent
        await called_once(pygw_proto.transport.write)

        pygw_proto.command_processor.submit_response("SE")
        with pytest.raises(SyntaxError):
            await task

    assert caplog.record_tuples == [
        (
            "pyotgw.commandprocessor",
            logging.DEBUG,
            "Sending command: PR with value I",
        ),
        (
            "pyotgw.commandprocessor",
            logging.DEBUG,
            "Response submitted. Queue size: 1",
        ),
        (
            "pyotgw.commandprocessor",
            logging.DEBUG,
            "Got possible response for command PR: SE",
        ),
        (
            "pyotgw.commandprocessor",
            logging.WARNING,
            (
                "Command PR failed with Syntax Error: The command contained an "
                "unexpected character or was incomplete., retrying..."
            ),
        ),
        (
            "pyotgw.commandprocessor",
            logging.DEBUG,
            "Response submitted. Queue size: 1",
        ),
        (
            "pyotgw.commandprocessor",
            logging.DEBUG,
            "Got possible response for command PR: SE",
        ),
    ]


@pytest.mark.asyncio
async def test_issue_cmd_with_data_on_line_before_response(caplog, pygw_proto):
    """Test issue_cmd with unexpected data in command queue."""
    loop = asyncio.get_running_loop()
    pygw_proto.transport.write = MagicMock()

    with caplog.at_level(logging.WARNING):
        task = loop.create_task(
            pygw_proto.command_processor.issue_cmd(
                v.OTGW_CMD_CONTROL_SETPOINT_2,
                20.501,
                1,
            )
        )

        await called_once(pygw_proto.transport.write)
        pygw_proto.transport.write.assert_called_once_with(b"C2=20.50\r\n")
        pygw_proto.transport.write.reset_mock()

        pygw_proto.command_processor.submit_response("InvalidCommand")
        await called_once(pygw_proto.transport.write)

        pygw_proto.command_processor.submit_response("C2: 20.50")
        assert await task == "20.50"

    assert caplog.record_tuples == [
        (
            "pyotgw.commandprocessor",
            logging.WARNING,
            "Unknown message in command queue: InvalidCommand",
        ),
        (
            "pyotgw.commandprocessor",
            logging.WARNING,
            (
                "Command C2 failed with Unknown message in command queue: "
                "InvalidCommand, retrying..."
            ),
        ),
    ]


@pytest.mark.asyncio
async def test_issue_cmd_with_bad_value_error(caplog, pygw_proto):
    """Test handling of Bad Value errors."""
    loop = asyncio.get_running_loop()
    pygw_proto.transport.write = MagicMock()

    with caplog.at_level(logging.WARNING):
        task = loop.create_task(
            pygw_proto.command_processor.issue_cmd(
                v.OTGW_CMD_CONTROL_HEATING_2,
                -1,
                2,
            )
        )
        await called_once(pygw_proto.transport.write)
        pygw_proto.transport.write.assert_called_once_with(b"H2=-1\r\n")
        pygw_proto.transport.write.reset_mock()

        pygw_proto.command_processor.submit_response("Error 03")
        await called_once(pygw_proto.transport.write)

        pygw_proto.command_processor.submit_response("H2: BV")
        await called_x_times(pygw_proto.transport.write, 2)
        pygw_proto.command_processor.submit_response("H2: BV")
        with pytest.raises(ValueError):
            await task

    assert caplog.record_tuples == [
        (
            "pyotgw.commandprocessor",
            logging.WARNING,
            (
                "Received Error 03. If this happens during a reset of the gateway it "
                "can be safely ignored."
            ),
        ),
        (
            "pyotgw.commandprocessor",
            logging.WARNING,
            (
                "Command H2 failed with Received Error 03. If this happens during a "
                "reset of the gateway it can be safely ignored., retrying..."
            ),
        ),
        (
            "pyotgw.commandprocessor",
            logging.WARNING,
            (
                "Command H2 failed with Bad Value: The command contained a data value "
                "that is not allowed or not supported on this version of the "
                "OpenTherm Gateway., retrying..."
            ),
        ),
    ]


@pytest.mark.asyncio
async def test_issue_cmd_reset(caplog, pygw_proto):
    """Test gateway reset handling."""
    loop = asyncio.get_running_loop()

    pygw_proto.transport.write = MagicMock()
    task = loop.create_task(
        pygw_proto.command_processor.issue_cmd(
            v.OTGW_CMD_MODE,
            "R",
            0,
        )
    )
    await called_once(pygw_proto.transport.write)
    pygw_proto.command_processor.submit_response("ThisGetsIgnored")
    pygw_proto.command_processor.submit_response("OpenTherm Gateway 4.3.5")

    assert await task is True


@pytest.mark.asyncio
async def test_issue_cmd_summary(caplog, pygw_proto):
    """Test PS command handling."""
    loop = asyncio.get_running_loop()

    pygw_proto.transport.write = MagicMock()
    task = loop.create_task(
        pygw_proto.command_processor.issue_cmd(
            v.OTGW_CMD_SUMMARY,
            1,
            0,
        )
    )
    await called_once(pygw_proto.transport.write)
    pygw_proto.command_processor.submit_response("PS: 1")
    pygw_proto.command_processor.submit_response(
        "part_2_will_normally_be_parsed_by_get_status",
    )

    assert await task == ["1", "part_2_will_normally_be_parsed_by_get_status"]
