"""Tests for pyotgw/messages.py"""

import pyotgw.messages as m
from pyotgw.messageprocessor import MessageProcessor


def test_message_registry():
    """Test message registry values."""
    for msgid, processing in m.REGISTRY.items():
        assert 0 <= int.from_bytes(msgid, "big") < 128
        assert isinstance(processing[m.M2S], list)
        assert isinstance(processing[m.S2M], list)

        for action in [*processing[m.M2S], *processing[m.S2M]]:
            assert hasattr(MessageProcessor, action[m.FUNC])
            assert isinstance(action[m.ARGS], tuple)
            assert isinstance(action[m.RETURNS], tuple)
