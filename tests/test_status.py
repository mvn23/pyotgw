"""Tests for pyotgw/status.py"""
import asyncio
import logging
from unittest.mock import MagicMock

import pytest

import pyotgw.vars as v
from tests.helpers import called_once


def test_reset(pygw_status):
    """Test StatusManager.reset()"""
    assert pygw_status.status == v.DEFAULT_STATUS

    pygw_status.submit_partial_update(v.OTGW, {"Test": "value"})

    assert pygw_status.status != v.DEFAULT_STATUS
    assert not pygw_status._updateq.empty()

    pygw_status.reset()

    assert pygw_status.status == v.DEFAULT_STATUS
    assert pygw_status._updateq.empty()


def test_status(pygw_status):
    """Test StatusManager.status()"""
    assert pygw_status.status == pygw_status._status
    assert pygw_status.status is not pygw_status._status


def test_delete_value(pygw_status):
    """Test StatusManager.delete_value()"""
    assert not pygw_status.delete_value("Invalid", v.OTGW_MODE)
    assert not pygw_status.delete_value(v.OTGW, v.OTGW_MODE)

    pygw_status.submit_partial_update(v.THERMOSTAT, {v.DATA_ROOM_SETPOINT: 20.5})
    pygw_status._updateq.get_nowait()

    assert pygw_status.delete_value(v.THERMOSTAT, v.DATA_ROOM_SETPOINT)
    assert pygw_status._updateq.get_nowait() == v.DEFAULT_STATUS


def test_submit_partial_update(caplog, pygw_status):
    """Test StatusManager.submit_partial_update()"""
    with caplog.at_level(logging.ERROR):
        assert not pygw_status.submit_partial_update("Invalid", {})

    assert pygw_status._updateq.empty()
    assert caplog.record_tuples == [
        (
            "pyotgw.status",
            logging.ERROR,
            "Invalid status part for update: Invalid",
        ),
    ]
    caplog.clear()

    with caplog.at_level(logging.ERROR):
        assert not pygw_status.submit_partial_update(v.OTGW, "Invalid")

    assert pygw_status._updateq.empty()
    assert caplog.record_tuples == [
        (
            "pyotgw.status",
            logging.ERROR,
            f"Update for {v.OTGW} is not a dict: Invalid",
        ),
    ]
    caplog.clear()

    pygw_status.submit_partial_update(v.BOILER, {v.DATA_CONTROL_SETPOINT: 1.5})
    pygw_status.submit_partial_update(v.OTGW, {v.OTGW_ABOUT: "test value"})
    pygw_status.submit_partial_update(v.THERMOSTAT, {v.DATA_ROOM_SETPOINT: 20})

    assert pygw_status.status == {
        v.BOILER: {v.DATA_CONTROL_SETPOINT: 1.5},
        v.OTGW: {v.OTGW_ABOUT: "test value"},
        v.THERMOSTAT: {v.DATA_ROOM_SETPOINT: 20},
    }
    assert pygw_status._updateq.qsize() == 3
    assert pygw_status._updateq.get_nowait() == {
        v.BOILER: {v.DATA_CONTROL_SETPOINT: 1.5},
        v.OTGW: {},
        v.THERMOSTAT: {},
    }
    assert pygw_status._updateq.get_nowait() == {
        v.BOILER: {v.DATA_CONTROL_SETPOINT: 1.5},
        v.OTGW: {v.OTGW_ABOUT: "test value"},
        v.THERMOSTAT: {},
    }
    assert pygw_status._updateq.get_nowait() == {
        v.BOILER: {v.DATA_CONTROL_SETPOINT: 1.5},
        v.OTGW: {v.OTGW_ABOUT: "test value"},
        v.THERMOSTAT: {v.DATA_ROOM_SETPOINT: 20},
    }


def test_submit_full_update(caplog, pygw_status):
    """Test StatusManager.submit_full_update()"""
    assert pygw_status.submit_full_update({})
    assert pygw_status._updateq.qsize() == 1
    assert pygw_status._updateq.get_nowait() == v.DEFAULT_STATUS

    with caplog.at_level(logging.ERROR):
        pygw_status.submit_full_update({"Invalid": {}})

    assert pygw_status._updateq.empty()
    assert caplog.record_tuples == [
        (
            "pyotgw.status",
            logging.ERROR,
            "Invalid status part for update: Invalid",
        ),
    ]
    caplog.clear()

    with caplog.at_level(logging.ERROR):
        pygw_status.submit_full_update({v.OTGW: "Invalid"})

    assert pygw_status._updateq.empty()
    assert caplog.record_tuples == [
        (
            "pyotgw.status",
            logging.ERROR,
            f"Update for {v.OTGW} is not a dict: Invalid",
        ),
    ]
    caplog.clear()

    pygw_status.submit_full_update(
        {
            v.BOILER: {v.DATA_CONTROL_SETPOINT: 1.5},
            v.OTGW: {v.OTGW_ABOUT: "test value"},
            v.THERMOSTAT: {v.DATA_ROOM_SETPOINT: 20},
        }
    )

    assert pygw_status.status == {
        v.BOILER: {v.DATA_CONTROL_SETPOINT: 1.5},
        v.OTGW: {v.OTGW_ABOUT: "test value"},
        v.THERMOSTAT: {v.DATA_ROOM_SETPOINT: 20},
    }
    assert pygw_status._updateq.qsize() == 1
    assert pygw_status._updateq.get_nowait() == {
        v.BOILER: {v.DATA_CONTROL_SETPOINT: 1.5},
        v.OTGW: {v.OTGW_ABOUT: "test value"},
        v.THERMOSTAT: {v.DATA_ROOM_SETPOINT: 20},
    }


def test_subscribe(pygw_status):
    """Test StatusManager.subscribe()"""

    def empty_callback():
        return

    assert pygw_status.subscribe(empty_callback)
    assert empty_callback in pygw_status._notify
    assert not pygw_status.subscribe(empty_callback)


def test_unsubscribe(pygw_status):
    """Test StatusManager.unsubscribe()"""

    def empty_callback():
        return

    assert not pygw_status.unsubscribe(empty_callback)
    pygw_status.subscribe(empty_callback)
    assert pygw_status.unsubscribe(empty_callback)
    assert empty_callback not in pygw_status._notify


@pytest.mark.asyncio
async def test_stop_reporting(pygw_status):
    """Test StatusManager.stop_reporting()"""
    assert isinstance(pygw_status._update_task, asyncio.Task)
    await pygw_status.cleanup()
    assert pygw_status._update_task is None


@pytest.mark.asyncio
async def test_process_updates(caplog, pygw_status):
    """Test StatusManager._process_updates()"""

    await pygw_status.cleanup()
    pygw_status.__init__()
    with caplog.at_level(logging.DEBUG):
        # Let the reporting routine start
        await asyncio.sleep(0)

    assert isinstance(pygw_status._update_task, asyncio.Task)
    assert caplog.record_tuples == [
        (
            "pyotgw.status",
            logging.DEBUG,
            "Starting reporting routine",
        ),
    ]
    caplog.clear()

    async def empty_callback_1(status):
        return

    async def empty_callback_2(status):
        return

    mock_callback_1 = MagicMock(side_effect=empty_callback_1)
    mock_callback_2 = MagicMock(side_effect=empty_callback_2)

    pygw_status.subscribe(mock_callback_1)
    pygw_status.subscribe(mock_callback_2)
    pygw_status.submit_partial_update(v.OTGW, {v.OTGW_ABOUT: "Test Value"})
    await asyncio.gather(called_once(mock_callback_1), called_once(mock_callback_2))

    for mock in (mock_callback_1, mock_callback_2):
        mock.assert_called_once_with(
            {
                v.BOILER: {},
                v.OTGW: {v.OTGW_ABOUT: "Test Value"},
                v.THERMOSTAT: {},
            }
        )
