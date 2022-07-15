"""Test for pyotgw/messageprocessor.py"""
import asyncio
import logging
import re
from unittest.mock import MagicMock, patch

import pytest

from pyotgw import vars as v
from tests.data import pygw_proto_messages
from tests.helpers import called_once

MATCH_PATTERN = r"^(T|B|R|A|E)([0-9A-F]{8})$"


@pytest.mark.asyncio
async def test_cleanup(pygw_message_processor):
    """Test MessageProcessor.cleanup()"""
    assert pygw_message_processor._task
    await pygw_message_processor.cleanup()
    assert not pygw_message_processor._task


def test_connection_lost(pygw_message_processor):
    """Test MessageProcessor.connection_lost()"""
    message = re.match(MATCH_PATTERN, "A01020304")
    pygw_message_processor.submit_matched_message(message)
    pygw_message_processor.submit_matched_message(message)
    pygw_message_processor.submit_matched_message(message)
    pygw_message_processor.connection_lost()
    assert pygw_message_processor._msgq.empty()


def test_submit_matched_message(caplog, pygw_message_processor):
    """Tests MessageProcessor.submit_matched_message()"""
    bad_match = re.match(MATCH_PATTERN, "E01020304")
    good_match = re.match(MATCH_PATTERN, "A01020304")

    pygw_message_processor.submit_matched_message(bad_match)
    assert pygw_message_processor._msgq.empty()

    with caplog.at_level(logging.DEBUG):
        pygw_message_processor.submit_matched_message(good_match)
    assert caplog.record_tuples == [
        (
            "pyotgw.messageprocessor",
            logging.DEBUG,
            "Added line to message queue. Queue size: 1",
        ),
    ]
    assert pygw_message_processor._msgq.get_nowait() == (
        "A",
        v.READ_DATA,
        b"\x02",
        b"\x03",
        b"\x04",
    )


def test_dissect_msg(caplog, pygw_message_processor):
    """Test MessageProcessor._dissect_msg"""
    pat = r"^(T|B|R|A|E)([0-9A-F]{8})$"
    test_matches = (
        re.match(pat, "A10203040"),
        re.match(pat, "EEEEEEEEE"),
        re.match(pat, "AEEEEEEEE"),
    )
    none_tuple = (None, None, None, None, None)

    assert pygw_message_processor._dissect_msg(test_matches[0]) == (
        "A",
        v.WRITE_DATA,
        b"\x20",
        b"\x30",
        b"\x40",
    )

    with caplog.at_level(logging.INFO):
        assert pygw_message_processor._dissect_msg(test_matches[1]) == none_tuple

    assert caplog.record_tuples == [
        (
            "pyotgw.messageprocessor",
            logging.INFO,
            "The OpenTherm Gateway received an erroneous message."
            " This is not a bug in pyotgw. Ignoring: EEEEEEEE",
        )
    ]

    assert pygw_message_processor._dissect_msg(test_matches[2]) == none_tuple


def test_get_msgtype(pygw_message_processor):
    """Test MessageProcessor._get_msgtype()"""
    assert pygw_message_processor._get_msgtype(int("11011111", 2)) == int("0101", 2)
    assert pygw_message_processor._get_msgtype(int("01000001", 2)) == int("0100", 2)


@pytest.mark.asyncio
async def test_process_msgs(caplog, pygw_message_processor):
    """Test MessageProcessor._process_msgs()"""
    test_case = (
        "B",
        v.READ_ACK,
        b"\x23",
        b"\x0A",
        b"\x01",
    )
    with patch.object(
        pygw_message_processor, "_process_msg"
    ) as process_msg, caplog.at_level(logging.DEBUG):
        task = asyncio.create_task(pygw_message_processor._process_msgs())
        pygw_message_processor._msgq.put_nowait(test_case)
        await called_once(process_msg)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    process_msg.assert_called_once_with(test_case)
    assert caplog.record_tuples == [
        ("pyotgw.messageprocessor", logging.DEBUG, "Processing: B 04 23 0A 01")
    ]


@pytest.mark.asyncio
async def test_process_msg(pygw_message_processor):
    """Test MessageProcessor._process_msg()"""
    # Test quirks
    test_case = (
        "B",
        v.READ_ACK,
        v.MSG_TROVRD,
        b"\x10",
        b"\x80",
    )

    with patch.object(
        pygw_message_processor, "_quirk_trovrd", return_value=None
    ) as quirk_trovrd:
        await pygw_message_processor._process_msg(test_case)

    quirk_trovrd.assert_called_once_with(
        v.BOILER,
        "B",
        b"\x10",
        b"\x80",
    )

    async def empty_coroutine(status):
        return

    status_callback = MagicMock(side_effect=empty_coroutine)
    pygw_message_processor.status_manager.subscribe(status_callback)

    for test_case, expected_result in pygw_proto_messages:
        pygw_message_processor.status_manager.reset()
        await pygw_message_processor._process_msg(test_case)
        if expected_result is not None:
            await called_once(status_callback)
            status_callback.assert_called_once_with(expected_result)
            status_callback.reset_mock()


@pytest.mark.asyncio
async def test_get_dict_update_for_action():
    """Test MessageProcessor._get_dict_update_for_action"""
    assert True  # Fully tested in test_process_msg()


@pytest.mark.asyncio
async def test_quirk_trovrd(pygw_message_processor):
    """Test MessageProcessor._quirk_trovrd()"""

    async def empty_coroutine(stat):
        return

    status_callback = MagicMock(side_effect=empty_coroutine)
    pygw_message_processor.status_manager.subscribe(status_callback)
    pygw_message_processor.status_manager.submit_partial_update(
        v.OTGW,
        {v.OTGW_THRM_DETECT: "I"},
    )
    await called_once(status_callback)
    status_callback.reset_mock()

    with patch.object(
        pygw_message_processor.command_processor,
        "issue_cmd",
        return_value="O=c19.5",
    ):
        await pygw_message_processor._quirk_trovrd(
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

    with patch.object(
        pygw_message_processor.command_processor,
        "issue_cmd",
        return_value="O=q---",
    ), patch.object(
        pygw_message_processor.status_manager,
        "submit_partial_update",
    ) as partial_update, patch.object(
        pygw_message_processor.status_manager,
        "delete_value",
    ) as delete_value:
        await pygw_message_processor._quirk_trovrd(
            v.THERMOSTAT,
            "A",
            b"\x15",
            b"\x40",
        )

    partial_update.assert_not_called()
    delete_value.assert_not_called()
    assert (
        v.DATA_ROOM_SETPOINT_OVRD
        in pygw_message_processor.status_manager.status[v.THERMOSTAT]
    )

    status_callback.reset_mock()
    await pygw_message_processor._quirk_trovrd(
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
    pygw_message_processor.status_manager.submit_partial_update(
        v.OTGW, {v.OTGW_THRM_DETECT: "D"}
    )
    await called_once(status_callback)
    status_callback.reset_mock()

    await pygw_message_processor._quirk_trovrd(
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
    pygw_message_processor.status_manager.submit_partial_update(
        v.OTGW, {v.OTGW_THRM_DETECT: "I"}
    )
    await called_once(status_callback)
    status_callback.reset_mock()

    with patch.object(
        pygw_message_processor.command_processor,
        "issue_cmd",
        return_value="O=N",
    ):
        await pygw_message_processor._quirk_trovrd(
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


def test_get_flag8(pygw_message_processor):
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
        assert pygw_message_processor._get_flag8(case) == res


def test_get_u8(pygw_message_processor):
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
        assert pygw_message_processor._get_u8(case) == res


def test_get_s8(pygw_message_processor):
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
        assert pygw_message_processor._get_s8(case) == res


def test_get_f8_8(pygw_message_processor):
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
        assert pygw_message_processor._get_f8_8(*case) == res


def test_get_u16(pygw_message_processor):
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
        assert pygw_message_processor._get_u16(*case) == res


def test_get_s16(pygw_message_processor):
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
        assert pygw_message_processor._get_s16(*case) == res
