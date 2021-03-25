"""Tests for pyotgw/protocol.py"""

import asyncio
import logging
import re
from unittest.mock import MagicMock, call, patch

import pytest

import pyotgw.vars as v
from tests.data import pygw_proto_messages
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
    pygw_proto._msgq.put_nowait("test msgq")

    with caplog.at_level(logging.ERROR):
        pygw_proto.connection_lost(None)
        pygw_proto.loop.run_until_complete(pygw_proto._msg_task)

    assert not pygw_proto.active
    for q in [pygw_proto._cmdq, pygw_proto._msgq]:
        assert q.empty()
    assert pygw_proto.status_manager.status == v.DEFAULT_STATUS
    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.ERROR,
            "Disconnected: None",
        ),
    ]


async def test_disconnect(pygw_proto):
    """Test OpenThermProtocol.disconnect()"""
    await pygw_proto.disconnect()

    pygw_proto._connected = True
    pygw_proto.transport.is_closing.return_value = False

    await pygw_proto.disconnect()

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
    message_expect = ("A", 1, b"\x2B", b"\x3C", b"\x4D")

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

    with caplog.at_level(logging.DEBUG):
        pygw_proto.line_received(test_lines[1])

    assert pygw_proto._received_lines == 1
    pygw_proto.activity_callback.assert_called_once()
    assert pygw_proto._msgq.qsize() == 1
    assert pygw_proto._msgq.get_nowait() == message_expect
    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.DEBUG,
            f"Received line 1: {test_lines[1]}",
        ),
        (
            "pyotgw.protocol",
            logging.DEBUG,
            "Added line 1 to message queue. Queue size: 1",
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


def test_dissect_msg(caplog, pygw_proto):
    """Test OpenThermProtocol._dissect_msg"""
    pat = r"^(T|B|R|A|E)([0-9A-F]{8})$"
    test_matches = (
        re.match(pat, "A10203040"),
        re.match(pat, "EEEEEEEEE"),
        re.match(pat, "AEEEEEEEE"),
    )
    none_tuple = (None, None, None, None, None)

    assert pygw_proto._dissect_msg(test_matches[0]) == (
        "A",
        v.WRITE_DATA,
        b"\x20",
        b"\x30",
        b"\x40",
    )

    with caplog.at_level(logging.INFO):
        assert pygw_proto._dissect_msg(test_matches[1]) == none_tuple

    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.INFO,
            "The OpenTherm Gateway received an erroneous message."
            " This is not a bug in pyotgw. Ignoring: EEEEEEEE",
        )
    ]

    assert pygw_proto._dissect_msg(test_matches[2]) == none_tuple


def test_get_msgtype(pygw_proto):
    """Test OpenThermProtocol._get_msgtype()"""
    assert pygw_proto._get_msgtype(int("11011111", 2)) == int("0101", 2)
    assert pygw_proto._get_msgtype(int("01000001", 2)) == int("0100", 2)


async def test_process_msgs(caplog, pygw_proto):
    """Test OpenThermProtocol._process_msgs()"""
    test_case = (
        "B",
        v.READ_ACK,
        b"\x23",
        b"\x0A",
        b"\x01",
    )
    with patch.object(pygw_proto, "_process_msg") as process_msg, caplog.at_level(
        logging.DEBUG
    ):
        task = pygw_proto.loop.create_task(pygw_proto._process_msgs())
        pygw_proto._msgq.put_nowait(test_case)
        await called_once(process_msg)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    process_msg.assert_called_once_with(test_case)
    assert caplog.record_tuples == [
        ("pyotgw.protocol", logging.DEBUG, "Processing: B 04 23 0A 01")
    ]


async def test_process_msg(pygw_proto):
    """Test OpenThermProtocol._process_msg()"""
    # Test quirks
    test_case = (
        "B",
        v.READ_ACK,
        v.MSG_TROVRD,
        b"\x10",
        b"\x80",
    )

    with patch.object(pygw_proto, "_quirk_trovrd", return_value=None) as quirk_trovrd:
        await pygw_proto._process_msg(test_case)

    quirk_trovrd.assert_called_once_with(
        v.BOILER,
        "B",
        b"\x10",
        b"\x80",
    )

    async def empty_coroutine(status):
        return

    status_callback = MagicMock(side_effect=empty_coroutine)
    pygw_proto.status_manager.subscribe(status_callback)

    for test_case, expected_result in pygw_proto_messages:
        pygw_proto.status_manager.reset()
        await pygw_proto._process_msg(test_case)
        if expected_result is not None:
            await called_once(status_callback)
            status_callback.assert_called_once_with(expected_result)
            status_callback.reset_mock()


async def test_get_dict_update_for_action():
    """Test OpenThermProtocol._get_dict_update_for_action"""
    assert True  # Fully tested in test_process_msg()


async def test_quirk_trovrd(pygw_proto):
    """Test OpenThermProtocol._quirk_trovrd()"""

    async def empty_coroutine(stat):
        return

    status_callback = MagicMock(side_effect=empty_coroutine)
    pygw_proto.status_manager.subscribe(status_callback)
    pygw_proto.status_manager.submit_partial_update(v.OTGW, {v.OTGW_THRM_DETECT: "I"})
    await called_once(status_callback)
    status_callback.reset_mock()

    with patch.object(pygw_proto, "issue_cmd", return_value="O=c19.5"):
        await pygw_proto._quirk_trovrd(
            v.THERMOSTAT,
            "A",
            b"\x15",
            b"\x40",
        )

    await called_once(status_callback)
    status_callback.assert_called_once_with(
        {
            v.BOILER: {},
            v.OTGW: {v.OTGW_THRM_DETECT: "I"},
            v.THERMOSTAT: {v.DATA_ROOM_SETPOINT_OVRD: 19.5},
        }
    )

    with patch.object(pygw_proto, "issue_cmd", return_value="O=q---",), patch.object(
        pygw_proto.status_manager,
        "submit_partial_update",
    ) as partial_update, patch.object(
        pygw_proto.status_manager,
        "delete_value",
    ) as delete_value:
        await pygw_proto._quirk_trovrd(
            v.THERMOSTAT,
            "A",
            b"\x15",
            b"\x40",
        )

    partial_update.assert_not_called()
    delete_value.assert_not_called()
    assert v.DATA_ROOM_SETPOINT_OVRD in pygw_proto.status_manager.status[v.THERMOSTAT]

    status_callback.reset_mock()
    await pygw_proto._quirk_trovrd(
        v.THERMOSTAT,
        "A",
        b"\x00",
        b"\x00",
    )
    await called_once(status_callback)
    status_callback.assert_called_once_with(
        {
            v.BOILER: {},
            v.OTGW: {v.OTGW_THRM_DETECT: "I"},
            v.THERMOSTAT: {},
        }
    )

    status_callback.reset_mock()
    pygw_proto.status_manager.submit_partial_update(v.OTGW, {v.OTGW_THRM_DETECT: "D"})
    await called_once(status_callback)
    status_callback.reset_mock()

    await pygw_proto._quirk_trovrd(
        v.THERMOSTAT,
        "A",
        b"\x15",
        b"\x40",
    )
    await called_once(status_callback)
    status_callback.assert_called_once_with(
        {
            v.BOILER: {},
            v.OTGW: {v.OTGW_THRM_DETECT: "D"},
            v.THERMOSTAT: {v.DATA_ROOM_SETPOINT_OVRD: 21.25},
        }
    )

    status_callback.reset_mock()
    pygw_proto.status_manager.submit_partial_update(v.OTGW, {v.OTGW_THRM_DETECT: "I"})
    await called_once(status_callback)
    status_callback.reset_mock()

    with patch.object(pygw_proto, "issue_cmd", return_value="O=N"):
        await pygw_proto._quirk_trovrd(
            v.THERMOSTAT,
            "A",
            b"\x15",
            b"\x40",
        )
    await called_once(status_callback)
    status_callback.assert_called_once_with(
        {
            v.BOILER: {},
            v.OTGW: {v.OTGW_THRM_DETECT: "I"},
            v.THERMOSTAT: {},
        }
    )


def test_get_flag8(pygw_proto):
    """Test pygw._get_flag8()"""
    test_cases = (
        (
            int("00000001", 2).to_bytes(1, "big"),
            [1, 0, 0, 0, 0, 0, 0, 0],
        ),
        (
            int("00000010", 2).to_bytes(1, "big"),
            [0, 1, 0, 0, 0, 0, 0, 0],
        ),
        (
            int("00000100", 2).to_bytes(1, "big"),
            [0, 0, 1, 0, 0, 0, 0, 0],
        ),
        (
            int("00001000", 2).to_bytes(1, "big"),
            [0, 0, 0, 1, 0, 0, 0, 0],
        ),
        (
            int("00010000", 2).to_bytes(1, "big"),
            [0, 0, 0, 0, 1, 0, 0, 0],
        ),
        (
            int("00100000", 2).to_bytes(1, "big"),
            [0, 0, 0, 0, 0, 1, 0, 0],
        ),
        (
            int("01000000", 2).to_bytes(1, "big"),
            [0, 0, 0, 0, 0, 0, 1, 0],
        ),
        (
            int("10000000", 2).to_bytes(1, "big"),
            [0, 0, 0, 0, 0, 0, 0, 1],
        ),
    )

    for case, res in test_cases:
        assert pygw_proto._get_flag8(case) == res


def test_get_u8(pygw_proto):
    """Test pygw._get_u8()"""
    test_cases = (
        (
            b"\x00",
            0,
        ),
        (
            b"\xFF",
            255,
        ),
    )

    for case, res in test_cases:
        assert pygw_proto._get_u8(case) == res


def test_get_s8(pygw_proto):
    """Test pygw._get_s8()"""
    test_cases = (
        (
            b"\x00",
            0,
        ),
        (
            b"\xFF",
            -1,
        ),
    )

    for case, res in test_cases:
        assert pygw_proto._get_s8(case) == res


def test_get_f8_8(pygw_proto):
    """Test pygw._get_f8_8()"""
    test_cases = (
        (
            (
                b"\x00",
                b"\x00",
            ),
            0.0,
        ),
        (
            (
                b"\xFF",
                b"\x80",
            ),
            -0.5,
        ),
    )

    for case, res in test_cases:
        assert pygw_proto._get_f8_8(*case) == res


def test_get_u16(pygw_proto):
    """Test pygw._get_u16()"""
    test_cases = (
        (
            (
                b"\x00",
                b"\x00",
            ),
            0,
        ),
        (
            (
                b"\xFF",
                b"\xFF",
            ),
            65535,
        ),
    )

    for case, res in test_cases:
        assert pygw_proto._get_u16(*case) == res


def test_get_s16(pygw_proto):
    """Test pygw._get_s16()"""
    test_cases = (
        (
            (
                b"\x00",
                b"\x00",
            ),
            0,
        ),
        (
            (
                b"\xFF",
                b"\xFF",
            ),
            -1,
        ),
    )

    for case, res in test_cases:
        assert pygw_proto._get_s16(*case) == res


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
