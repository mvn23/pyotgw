import asyncio
from unittest.mock import MagicMock, patch

import pytest

import pyotgw


@pytest.fixture
def pygw():
    """Return a basic pyotgw object"""
    return pyotgw.pyotgw()


@pytest.fixture
async def pygw_proto(pygw):
    """Return a "connected" protocol object"""
    trans = MagicMock(loop=asyncio.get_running_loop())
    proto = pyotgw.protocol.OpenThermProtocol()
    pygw._transport = trans
    pygw._protocol = proto
    with patch("pyotgw.protocol.OpenThermProtocol._process_msgs", return_value=None):
        proto.connection_made(trans)
    return proto


@pytest.fixture(autouse=True)
async def check_task_cleanup():
    loop = asyncio.get_running_loop()
    task_count = len(asyncio.all_tasks(loop))

    yield

    assert len(asyncio.all_tasks(loop)) == task_count, "Test is leaving tasks behind!"
