from asyncio import get_running_loop
from unittest.mock import MagicMock, patch

import pyotgw
import pytest
from serial_asyncio import SerialTransport


@pytest.fixture
def pygw():
    """Return a basic pyotgw object"""
    return pyotgw.pyotgw()


@pytest.fixture
async def pygw_proto(pygw):
    """Return a "connected" protocol object"""
    trans = MagicMock(spec=SerialTransport, loop=get_running_loop())
    proto = pyotgw.protocol.protocol()
    pygw._transport = trans
    pygw._protocol = proto
    with patch("pyotgw.protocol.protocol._process_msgs", return_value=None):
        proto.connection_made(trans)
    return proto
