import asyncio
import copy
import logging
import re
from unittest.mock import MagicMock, call, patch

import pytest

import pyotgw.vars as v
from tests.data import pygw_proto_messages
from tests.helpers import has_been_called_x_times

pytestmark = pytest.mark.asyncio


def test_connection_made(pygw_proto):
    """Test OpenThermProtocol.connection_made()"""
    # pygw_proto already calls connection_made()
    assert pygw_proto.connected


def test_connection_lost(caplog, pygw_proto):
    """Test OpenThermProtocol.connection_lost()"""

    async def empty_callback(status):
        return

    pygw_proto._active = True
    pygw_proto._report_task = MagicMock(return_value=asyncio.Task(asyncio.sleep(0)))
    pygw_proto._cmdq.put_nowait("test cmdq")
    pygw_proto._updateq.put_nowait("test updateq")
    pygw_proto._msgq.put_nowait("test msgq")
    pygw_proto._update_cb = MagicMock(side_effect=empty_callback)

    with caplog.at_level(logging.ERROR):
        pygw_proto.connection_lost(None)
        pygw_proto.loop.run_until_complete(asyncio.sleep(0))

    assert not pygw_proto.active()
    pygw_proto._report_task.cancel.assert_called_once()
    for q in [pygw_proto._cmdq, pygw_proto._updateq, pygw_proto._msgq]:
        assert q.empty()
    assert pygw_proto.status == v.DEFAULT_STATUS
    pygw_proto._update_cb.assert_called_once_with(v.DEFAULT_STATUS)
    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.ERROR,
            "Disconnected: None",
        ),
    ]


async def test_disconnect(pygw_proto):
    """Test OpenThermProtocol.disconnect()"""
    with patch.object(
        pygw_proto,
        "watchdog_active",
        return_value=True,
    ) as wd_active, patch.object(pygw_proto, "cancel_watchdog") as cancel_watchdog:
        await pygw_proto.disconnect()

    wd_active.assert_called_once()
    cancel_watchdog.assert_called_once()

    pygw_proto.connected = True
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

        assert pygw_proto.active()
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


def test_watchdog_active(pygw_proto):
    """Test OpenThermProtocol.watchdog_active()"""
    assert not pygw_proto.watchdog_active()
    pygw_proto._watchdog_task = asyncio.Future()
    assert pygw_proto.watchdog_active()


def test_setup_watchdog(pygw_proto):
    """Test OpenThermProtocol.setup_watchdog()"""

    def cb():
        return

    with patch.object(
        pygw_proto,
        "_watchdog",
    ) as wd:
        pygw_proto.setup_watchdog(cb, 3)

    assert pygw_proto._watchdog_timeout == 3
    assert pygw_proto._watchdog_cb == cb
    wd.assert_called_once_with(3)

    pygw_proto.loop.run_until_complete(pygw_proto._watchdog_task)


async def test_cancel_watchdog(caplog, pygw_proto):
    """Test OpenThermProtocol.cancel_watchdog()"""
    with caplog.at_level(logging.DEBUG):
        await pygw_proto.cancel_watchdog()

    assert caplog.records == []

    pygw_proto._watchdog_task = pygw_proto.loop.create_task(asyncio.sleep(0))
    with patch.object(
        pygw_proto,
        "watchdog_active",
        return_value=True,
    ), caplog.at_level(logging.DEBUG):
        await pygw_proto.cancel_watchdog()

    assert pygw_proto._watchdog_task is None
    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.DEBUG,
            "Canceling Watchdog task.",
        ),
    ]


async def test_inform_watchdog(caplog, pygw_proto):
    """Test pyotgw._inform_watchdog()"""
    await pygw_proto._inform_watchdog()

    assert caplog.records == []

    pygw_proto._watchdog_task = pygw_proto.loop.create_task(asyncio.sleep(0))
    pygw_proto._watchdog_timeout = 3
    with patch.object(
        pygw_proto,
        "_watchdog",
    ) as wd, caplog.at_level(logging.DEBUG):
        await pygw_proto._inform_watchdog()

    wd.assert_called_once_with(3)
    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.DEBUG,
            "Watchdog timer reset!",
        ),
    ]


async def test_watchdog(caplog, pygw_proto):
    """Test OpenThermProtocol._watchdog()"""

    async def empty_callback():
        return

    pygw_proto._watchdog_cb = MagicMock(side_effect=empty_callback)

    with patch.object(
        pygw_proto,
        "cancel_watchdog",
    ) as cancel_wd, caplog.at_level(logging.DEBUG):
        await pygw_proto._watchdog(0)

    for item in [
        (
            "pyotgw.protocol",
            logging.DEBUG,
            "Watchdog triggered!",
        ),
        (
            "pyotgw.protocol",
            logging.DEBUG,
            "Internal read buffer content: ",
        ),
        (
            "pyotgw.protocol",
            logging.DEBUG,
            "Serial input buffer size: 1",
        ),
    ]:
        assert item in caplog.record_tuples

    cancel_wd.assert_called_once()
    pygw_proto._watchdog_cb.assert_called_once()

    pygw_proto._readbuf = None
    with patch.object(
        pygw_proto,
        "cancel_watchdog",
    ) as cancel_wd, caplog.at_level(logging.DEBUG):
        await pygw_proto._watchdog(0)

    assert caplog.record_tuples[-1] == (
        "pyotgw.protocol",
        logging.DEBUG,
        "Could not generate debug output during disconnect. "
        "Reported error: 'NoneType' object has no attribute 'hex'",
    )


def test_line_received(caplog, pygw_proto):
    """Test OpenThermProtocol.line_received()"""
    test_lines = ("BCDEF", "A1A2B3C4D", "MustBeCommand", "AlsoCommand")
    message_expect = ("A", b"\x1A", b"\x2B", b"\x3C", b"\x4D")

    with patch.object(
        pygw_proto,
        "_inform_watchdog",
    ) as inform_watchdog, caplog.at_level(logging.DEBUG):
        pygw_proto.line_received(test_lines[0])

    # required for cleanup
    pygw_proto.loop.run_until_complete(asyncio.sleep(0))

    inform_watchdog.assert_called_once()
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
    caplog.clear()

    with patch.object(pygw_proto, "_inform_watchdog",) as inform_watchdog, patch.object(
        pygw_proto,
        "_dissect_msg",
        return_value=message_expect,
    ) as dissect_msg, caplog.at_level(logging.DEBUG):
        pygw_proto.line_received(test_lines[1])

    # required for cleanup
    pygw_proto.loop.run_until_complete(asyncio.sleep(0))

    assert pygw_proto._received_lines == 1
    inform_watchdog.assert_called_once()
    dissect_msg.assert_called_once()
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
    caplog.clear()

    with patch.object(
        pygw_proto,
        "_inform_watchdog",
    ) as inform_watchdog, caplog.at_level(logging.DEBUG):
        pygw_proto.line_received(test_lines[2])

    # required for cleanup
    pygw_proto.loop.run_until_complete(asyncio.sleep(0))

    assert pygw_proto._received_lines == 2
    inform_watchdog.assert_called_once()
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
    caplog.clear()

    with patch.object(pygw_proto, "_inform_watchdog") as inform_watchdog, patch.object(
        pygw_proto._cmdq, "put_nowait", side_effect=asyncio.QueueFull
    ) as put_nowait, caplog.at_level(logging.ERROR):
        pygw_proto.line_received(test_lines[3])

    # required for cleanup
    pygw_proto.loop.run_until_complete(asyncio.sleep(0))

    inform_watchdog.assert_called_once()
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
        await has_been_called_x_times(process_msg, 1)

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
    pygw_proto.status[v.BOILER]["is_boiler"] = True

    with patch.object(pygw_proto, "_quirk_trovrd", return_value=None) as quirk_trovrd:
        await pygw_proto._process_msg(test_case)

    quirk_trovrd.assert_called_once_with(
        {"is_boiler": True},
        "B",
        b"\x10",
        b"\x80",
    )
    pygw_proto.status = copy.deepcopy(v.DEFAULT_STATUS)

    for test_case, expected_result in pygw_proto_messages:
        await pygw_proto._process_msg(test_case)
        if expected_result is not None:
            assert pygw_proto._updateq.qsize() == 1
            assert pygw_proto._updateq.get_nowait() == expected_result
        pygw_proto.status = copy.deepcopy(v.DEFAULT_STATUS)


async def test_quirk_trovrd(pygw_proto):
    """Test OpenThermProtocol._quirk_trovrd()"""
    pygw_proto.status[v.OTGW][v.OTGW_THRM_DETECT] = "I"

    with patch.object(pygw_proto, "issue_cmd", return_value="O=c19.5"):
        await pygw_proto._quirk_trovrd(
            pygw_proto.status[v.THERMOSTAT],
            "A",
            b"\x15",
            b"\x40",
        )

    assert pygw_proto._updateq.get_nowait() == {
        v.BOILER: {},
        v.OTGW: {v.OTGW_THRM_DETECT: "I"},
        v.THERMOSTAT: {v.DATA_ROOM_SETPOINT_OVRD: 19.5},
    }

    with patch.object(pygw_proto, "issue_cmd", return_value="O=q---"):
        await pygw_proto._quirk_trovrd(
            pygw_proto.status[v.THERMOSTAT],
            "A",
            b"\x15",
            b"\x40",
        )

    with pytest.raises(asyncio.QueueEmpty):
        pygw_proto._updateq.get_nowait()
    assert v.DATA_ROOM_SETPOINT_OVRD in pygw_proto.status[v.THERMOSTAT]

    await pygw_proto._quirk_trovrd(
        pygw_proto.status[v.THERMOSTAT],
        "A",
        b"\x00",
        b"\x00",
    )
    assert pygw_proto._updateq.get_nowait() == {
        v.BOILER: {},
        v.OTGW: {v.OTGW_THRM_DETECT: "I"},
        v.THERMOSTAT: {},
    }

    pygw_proto.status[v.OTGW][v.OTGW_THRM_DETECT] = "D"
    await pygw_proto._quirk_trovrd(
        pygw_proto.status[v.THERMOSTAT],
        "A",
        b"\x15",
        b"\x40",
    )
    assert pygw_proto._updateq.get_nowait() == {
        v.BOILER: {},
        v.OTGW: {v.OTGW_THRM_DETECT: "D"},
        v.THERMOSTAT: {v.DATA_ROOM_SETPOINT_OVRD: 21.25},
    }

    pygw_proto.status[v.OTGW][v.OTGW_THRM_DETECT] = "I"
    with patch.object(pygw_proto, "issue_cmd", return_value="O=N"):
        await pygw_proto._quirk_trovrd(
            pygw_proto.status[v.THERMOSTAT],
            "A",
            b"\x15",
            b"\x40",
        )

    assert pygw_proto._updateq.get_nowait() == {
        v.BOILER: {},
        v.OTGW: {v.OTGW_THRM_DETECT: "I"},
        v.THERMOSTAT: {},
    }


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


async def test_report(caplog, pygw_proto):
    """Test OpenThermProtocol._report()"""

    async def empty_callback(status):
        return

    loop = asyncio.get_running_loop()
    pygw_proto._updateq.put_nowait(copy.deepcopy(v.DEFAULT_STATUS))
    pygw_proto._update_cb = MagicMock(side_effect=empty_callback)
    pygw_proto.status = {}

    with caplog.at_level(logging.DEBUG):
        pygw_proto._report_task = loop.create_task(pygw_proto._report())
        await has_been_called_x_times(pygw_proto._update_cb, 1)

    assert isinstance(pygw_proto._report_task, asyncio.Task)
    pygw_proto._update_cb.assert_called_once_with(v.DEFAULT_STATUS)
    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.DEBUG,
            "Starting reporting routine",
        ),
    ]
    caplog.clear()

    pygw_proto._report_task.cancel()
    with caplog.at_level(logging.DEBUG):
        await pygw_proto._report_task

    assert pygw_proto._report_task is None
    assert caplog.record_tuples == [
        (
            "pyotgw.protocol",
            logging.DEBUG,
            "Stopping reporting routine",
        ),
    ]


def test_set_update_cb(pygw_proto):
    """Test OpenThermProtocol.set_update_cb()"""

    async def empty_callback(status):
        return

    initial_task = MagicMock()
    initial_task.cancelled = MagicMock(return_value=False)
    initial_task.cancel = MagicMock(return_value=None)

    pygw_proto._report_task = initial_task

    with patch.object(pygw_proto, "_report", return_value=None) as report:
        pygw_proto.set_update_cb(empty_callback)

    initial_task.cancel.assert_called_once()
    report.assert_called_once()
    assert pygw_proto._update_cb == empty_callback


async def test_issue_cmd(caplog, pygw_proto):
    """Test OpenThermProtocol.issue_cmd()"""
    pygw_proto.connected = False
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
    pygw_proto.connected = True
    pygw_proto._cmdq.put_nowait("thisshouldbecleared")
    pygw_proto.transport.write = MagicMock()

    with caplog.at_level(logging.DEBUG):
        task = loop.create_task(pygw_proto.issue_cmd(v.OTGW_CMD_REPORT, "I", 1))
        while not pygw_proto._cmdq.empty():
            await asyncio.sleep(0)

        assert pygw_proto._cmdq.empty()
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
        while not pygw_proto.transport.write.called:
            await asyncio.sleep(0)
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
        while not pygw_proto.transport.write.called:
            await asyncio.sleep(0)
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
    while not pygw_proto.transport.write.called:
        await asyncio.sleep(0)
    pygw_proto._cmdq.put_nowait("ThisGetsIgnored")
    pygw_proto._cmdq.put_nowait("OpenTherm Gateway 4.3.5")

    assert await task is True

    pygw_proto.transport.write = MagicMock()
    task = loop.create_task(pygw_proto.issue_cmd(v.OTGW_CMD_SUMMARY, 1, 0))
    while not pygw_proto.transport.write.called:
        await asyncio.sleep(0)
    pygw_proto._cmdq.put_nowait("PS: 1")
    pygw_proto._cmdq.put_nowait("part_2_will_normally_be_parsed_by_get_status")

    assert await task == ["1", "part_2_will_normally_be_parsed_by_get_status"]


def test_active(pygw_proto):
    """Test OpenThermProtocol.active()"""
    pygw_proto._active = False
    assert pygw_proto.active() is False
    pygw_proto._active = True
    assert pygw_proto.active() is True


async def test_init_and_wait_for_activity(pygw_proto):
    """Test OpenThermProtocol.init_and_wait_for_activity()"""
    loop = asyncio.get_running_loop()

    with patch.object(pygw_proto, "issue_cmd") as issue_cmd, patch.object(
        pygw_proto, "active", side_effect=[False, True]
    ) as active:
        task = loop.create_task(pygw_proto.init_and_wait_for_activity())
        while active.call_count < 1:
            await asyncio.sleep(0)
        pygw_proto._active = True
        await task
    assert issue_cmd.call_count == 1
