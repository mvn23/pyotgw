import pyotgw.messages as m
from pyotgw.protocol import protocol


def test_message_registry():
    """Test message registry values."""
    for msgid, processing in m.REGISTRY.items():
        assert 0 <= int.from_bytes(msgid, "big") < 128
        assert type(processing[m.M2S]) == list
        assert type(processing[m.S2M]) == list

        for action in [*processing[m.M2S], *processing[m.S2M]]:
            assert hasattr(protocol, action[m.FUNC])
            assert type(action[m.ARGS]) == tuple
            assert type(action[m.RETURNS]) == tuple
