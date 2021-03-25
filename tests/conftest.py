"""Config and fixtures for pyotgw tests"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

import pyotgw
from pyotgw.connection import ConnectionManager, ConnectionWatchdog
from pyotgw.status import StatusManager


@pytest.fixture
async def pygw():
    """Return a basic pyotgw object"""
    gw = pyotgw.pyotgw()
    await gw.connection.watchdog.stop()
    yield gw
    await gw.cleanup()


@pytest.fixture
async def pygw_proto(pygw):
    """Return a "connected" protocol object"""

    async def empty_coroutine():
        return

    trans = MagicMock(loop=asyncio.get_running_loop())
    activity_callback = MagicMock(side_effect=empty_coroutine)
    proto = pyotgw.protocol.OpenThermProtocol(pygw.status, activity_callback)
    proto.activity_callback = activity_callback
    pygw._transport = trans
    pygw._protocol = proto
    with patch("pyotgw.protocol.OpenThermProtocol._process_msgs", return_value=None):
        proto.connection_made(trans)
    return proto


@pytest.fixture
async def pygw_status():
    """Return a StatusManager object"""
    status_manager = StatusManager()
    yield status_manager
    await status_manager.cleanup()


@pytest.fixture
async def pygw_conn(pygw_status):
    """Return a ConnectionManager object"""
    connection_manager = ConnectionManager(pygw_status)
    yield connection_manager
    await connection_manager.watchdog.stop()


@pytest.fixture
async def pygw_watchdog():
    """Return a ConnectionWatchdog object"""
    watchdog = ConnectionWatchdog()
    yield watchdog
    await watchdog.stop()


@pytest.fixture(autouse=True)
async def check_task_cleanup():
    loop = asyncio.get_running_loop()
    task_count = len(asyncio.all_tasks(loop))

    yield

    assert len(asyncio.all_tasks(loop)) == task_count, "Test is leaving tasks behind!"
