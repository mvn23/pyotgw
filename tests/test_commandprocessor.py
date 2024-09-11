"""Tests for pyotgw/commandprocessor.py"""

import asyncio
import logging
from unittest.mock import MagicMock, call, patch

import pytest

from pyotgw.types import OpenThermCommand
from tests.helpers import called_once, let_queue_drain


@pytest.mark.asyncio
async def test_submit_response_queuefull(caplog, pygw_proto):
    """Test queuefull on submit_response()"""
    test_lines = ("BCDEF", "A1A2B3C4D", "MustBeCommand", "AlsoCommand")
    with patch.object(
        pygw_proto.command_processor._cmdq, "put_nowait", side_effect=asyncio.QueueFull
    ) as put_nowait, caplog.at_level(logging.ERROR):
        pygw_proto.line_received(test_lines[3])

    pygw_proto.activity_callback.assert_called_once()
    put_nowait.assert_called_once_with(test_lines[3])
    assert pygw_proto.command_processor._cmdq.qsize() == 0
    assert caplog.record_tuples == [
        (
            "pyotgw.commandprocessor",
            logging.ERROR,
            f"Queue full, discarded message: {test_lines[3]}",
        ),
    ]


@pytest.mark.asyncio
async def test_issue_cmd(caplog, pygw_proto):
    """Test OpenThermProtocol.issue_cmd()"""
    pygw_proto._connected = False
    with caplog.at_level(logging.DEBUG):
        assert (
            await pygw_proto.command_processor.issue_cmd(OpenThermCommand.SUMMARY, 1, 0)
            is None
        )

    assert caplog.record_tuples == [
        (
            "pyotgw.commandprocessor",
            logging.DEBUG,
            f"Serial transport closed, not sending command {OpenThermCommand.SUMMARY}",
        ),
    ]
    caplog.clear()

    loop = asyncio.get_running_loop()
    pygw_proto._connected = True
    pygw_proto.command_processor._cmdq.put_nowait("thisshouldbecleared")
    pygw_proto.transport.write = MagicMock()

    with caplog.at_level(logging.DEBUG):
        task = loop.create_task(
            pygw_proto.command_processor.issue_cmd(
                OpenThermCommand.REPORT,
                "I",
                1,
            )
        )
        await let_queue_drain(pygw_proto.command_processor._cmdq)

        pygw_proto.transport.write.assert_called_once_with(b"PR=I\r\n")
        assert caplog.record_tuples == [
            (
                "pyotgw.commandprocessor",
                logging.DEBUG,
                "Clearing leftover message from command queue: thisshouldbecleared",
            ),
            (
                "pyotgw.commandprocessor",
                logging.DEBUG,
                f"Sending command: {OpenThermCommand.REPORT} with value I",
            ),
        ]
        caplog.clear()

        pygw_proto.command_processor.submit_response("SE")
        pygw_proto.command_processor.submit_response("SE")
        with pytest.raises(SyntaxError):
            await task

    assert pygw_proto.transport.write.call_args_list == [
        call(b"PR=I\r\n"),
        call(b"PR=I\r\n"),
    ]

    assert caplog.record_tuples == [
        (
            "pyotgw.commandprocessor",
            logging.DEBUG,
            "Response submitted. Queue size: 1",
        ),
        (
            "pyotgw.commandprocessor",
            logging.DEBUG,
            "Response submitted. Queue size: 2",
        ),
        (
            "pyotgw.commandprocessor",
            logging.DEBUG,
            f"Got possible response for command {OpenThermCommand.REPORT}: SE",
        ),
        (
            "pyotgw.commandprocessor",
            logging.WARNING,
            f"Command {OpenThermCommand.REPORT} failed with SE, retrying...",
        ),
        (
            "pyotgw.commandprocessor",
            logging.DEBUG,
            f"Got possible response for command {OpenThermCommand.REPORT}: SE",
        ),
    ]
    caplog.clear()

    pygw_proto.transport.write = MagicMock()
    with caplog.at_level(logging.WARNING):
        task = loop.create_task(
            pygw_proto.command_processor.issue_cmd(
                OpenThermCommand.CONTROL_SETPOINT_2,
                20.501,
                1,
            )
        )
        await called_once(pygw_proto.transport.write)
        pygw_proto.transport.write.assert_called_once_with(b"C2=20.50\r\n")
        pygw_proto.command_processor.submit_response("InvalidCommand")
        pygw_proto.command_processor.submit_response(
            f"{OpenThermCommand.CONTROL_SETPOINT_2}: 20.50"
        )
        assert await task == "20.50"

    assert pygw_proto.transport.write.call_args_list == [
        call(b"C2=20.50\r\n"),
        call(b"C2=20.50\r\n"),
    ]
    assert caplog.record_tuples == [
        (
            "pyotgw.commandprocessor",
            logging.WARNING,
            "Unknown message in command queue: InvalidCommand",
        ),
        (
            "pyotgw.commandprocessor",
            logging.WARNING,
            f"Command {OpenThermCommand.CONTROL_SETPOINT_2} failed with InvalidCommand, retrying...",
        ),
    ]
    caplog.clear()

    pygw_proto.transport.write = MagicMock()
    with caplog.at_level(logging.WARNING):
        task = loop.create_task(
            pygw_proto.command_processor.issue_cmd(
                OpenThermCommand.CONTROL_HEATING_2,
                -1,
                2,
            )
        )
        await called_once(pygw_proto.transport.write)
        pygw_proto.transport.write.assert_called_once_with(b"H2=-1\r\n")
        pygw_proto.command_processor.submit_response("Error 03")
        pygw_proto.command_processor.submit_response(
            f"{OpenThermCommand.CONTROL_HEATING_2}: BV"
        )
        pygw_proto.command_processor.submit_response(
            f"{OpenThermCommand.CONTROL_HEATING_2}: BV"
        )
        with pytest.raises(ValueError):
            await task

    assert caplog.record_tuples == [
        (
            "pyotgw.commandprocessor",
            logging.WARNING,
            "Received Error 03. "
            "If this happens during a reset of the gateway it can be safely ignored.",
        ),
        (
            "pyotgw.commandprocessor",
            logging.WARNING,
            f"Command {OpenThermCommand.CONTROL_HEATING_2} failed with Error 03, retrying...",
        ),
        (
            "pyotgw.commandprocessor",
            logging.WARNING,
            f"Command {OpenThermCommand.CONTROL_HEATING_2} failed with {OpenThermCommand.CONTROL_HEATING_2}: BV, retrying...",
        ),
    ]

    pygw_proto.transport.write = MagicMock()
    task = loop.create_task(
        pygw_proto.command_processor.issue_cmd(
            OpenThermCommand.MODE,
            "R",
            0,
        )
    )
    await called_once(pygw_proto.transport.write)
    pygw_proto.command_processor.submit_response("ThisGetsIgnored")
    pygw_proto.command_processor.submit_response("OpenTherm Gateway 4.3.5")

    assert await task is True

    pygw_proto.transport.write = MagicMock()
    task = loop.create_task(
        pygw_proto.command_processor.issue_cmd(
            OpenThermCommand.SUMMARY,
            1,
            0,
        )
    )
    await called_once(pygw_proto.transport.write)
    pygw_proto.command_processor.submit_response(f"{OpenThermCommand.SUMMARY}: 1")
    pygw_proto.command_processor.submit_response(
        "part_2_will_normally_be_parsed_by_get_status",
    )

    assert await task == ["1", "part_2_will_normally_be_parsed_by_get_status"]
