import asyncio
import copy
import logging
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pyotgw.vars as v
import pytest
import serial
from tests.data import pygw_reports, pygw_status
from tests.helpers import has_been_called_x_times

pytestmark = pytest.mark.asyncio


async def test_connect_success_and_reconnect_with_gpio(caplog, pygw, pygw_proto):
    """Test pyotgw.connect()"""
    loop = asyncio.get_running_loop()

    with patch.object(pygw, "get_reports", return_value={}), patch.object(
        pygw, "get_status", return_value={},
    ), patch.object(pygw, "_poll_gpio") as poll_gpio, patch.object(
        pygw_proto, "init_and_wait_for_activity",
    ) as init_and_wait, patch.object(
        pygw_proto, "set_update_cb",
    ) as set_update_cb, patch(
        "serial_asyncio.create_serial_connection",
        return_value=(pygw_proto.transport, pygw_proto),
    ), caplog.at_level(
        logging.DEBUG
    ):
        status = await pygw.connect(loop, "loop://")
        await asyncio.sleep(0)

        assert status == v.DEFAULT_STATUS
        init_and_wait.assert_called_once()
        set_update_cb.assert_called_once()
        poll_gpio.assert_called_once()

        pygw._gpio_task = loop.create_task(asyncio.sleep(0))
        await pygw._protocol.cancel_watchdog()
        await pygw._protocol._watchdog_cb()
        await asyncio.sleep(0)

        for item in [
            ("pyotgw.pyotgw", logging.DEBUG, "Scheduling reconnect..."),
            (
                "pyotgw.pyotgw",
                logging.DEBUG,
                "Reconnecting to serial device on loop://",
            ),
        ]:
            assert item in caplog.record_tuples

        await pygw.disconnect()


async def test_connect_serialexception(caplog, pygw):
    """Test pyotgw.connect() with SerialException"""
    loop = asyncio.get_running_loop()

    with patch(
        "serial_asyncio.create_serial_connection",
        side_effect=serial.serialutil.SerialException,
    ) as create_serial_connection, patch.object(
        pygw, "_get_retry_timeout", return_value=0,
    ) as loops_done:
        task = loop.create_task(pygw.connect(loop, "loop://"))

        await has_been_called_x_times(loops_done, 2)

        assert type(pygw._attempt_connect) == asyncio.Task
        assert len(caplog.records) == 1
        assert caplog.record_tuples == [
            (
                "pyotgw.pyotgw",
                logging.ERROR,
                "Could not connect to serial device on loop://. "
                "Will keep trying. Reported error was: ",
            ),
        ]
        assert create_serial_connection.call_count > 1

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


async def test_connect_cancel(pygw):
    """Test pyotgw.connect() with CancelledError"""
    loop = asyncio.get_running_loop()

    with patch(
        "serial_asyncio.create_serial_connection", side_effect=asyncio.CancelledError,
    ) as create_serial_connection:
        status = await pygw.connect(loop, "loop://", inactivity_timeout=0)

    assert status == {}
    create_serial_connection.assert_called_once()


async def test_connect_timeouterror(caplog, pygw, pygw_proto):
    """Test pyotgw.connect() with TimeoutError"""

    async def empty_callback():
        return

    loop = asyncio.get_running_loop()

    pygw_proto.init_and_wait_for_activity = MagicMock(side_effect=asyncio.TimeoutError)
    pygw_proto.disconnect = MagicMock(side_effect=empty_callback)

    with patch.object(pygw, "_get_retry_timeout", return_value=0,) as loops_done, patch(
        "serial_asyncio.create_serial_connection",
        return_value=(pygw_proto.transport, pygw_proto),
    ), caplog.at_level(logging.DEBUG):
        task = loop.create_task(pygw.connect(loop, "loop://"))
        await has_been_called_x_times(loops_done, 2)

        assert type(pygw._attempt_connect) == asyncio.Task
        assert len(caplog.records) == 1
        assert caplog.record_tuples == [
            (
                "pyotgw.pyotgw",
                logging.ERROR,
                "The serial device on loop:// is not responding. " "Will keep trying.",
            ),
        ]
        assert pygw_proto.init_and_wait_for_activity.call_count > 1
        assert pygw_proto.disconnect.call_count > 1

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


async def test_connect_short_inactivity_timeout(caplog, pygw, pygw_proto):
    """Test pyotgw.connect() with a (too) short timeout"""
    loop = asyncio.get_running_loop()

    with patch.object(pygw, "get_reports", return_value={}), patch.object(
        pygw, "get_status", return_value={},
    ), patch.object(pygw, "_poll_gpio"), patch.object(
        pygw_proto, "init_and_wait_for_activity",
    ) as init_and_wait, patch.object(
        pygw_proto, "set_update_cb",
    ) as set_update_cb, patch(
        "serial_asyncio.create_serial_connection",
        return_value=(pygw_proto.transport, pygw_proto),
    ), caplog.at_level(
        logging.ERROR
    ):
        status = await pygw.connect(loop, "loop://", inactivity_timeout=1)

    assert status == v.DEFAULT_STATUS
    init_and_wait.assert_called_once()
    set_update_cb.assert_called_once()
    assert caplog.record_tuples == [
        (
            "pyotgw.pyotgw",
            logging.ERROR,
            "Inactivity timeout too low. Should be at least 3 seconds, got 1",
        ),
    ]


async def test_disconnect_while_connecting(pygw):
    """Test pyotgw.disconnect()"""
    loop = asyncio.get_running_loop()

    pygw._attempt_connect = loop.create_task(asyncio.sleep(0))
    pygw._connected = False

    with patch("pyotgw.protocol.protocol.disconnect") as protocol_disconnect:
        await pygw.disconnect()
    with pytest.raises(asyncio.CancelledError):
        await pygw._attempt_connect
    assert not protocol_disconnect.called


def test_get_room_temp(pygw):
    """Test pyotgw.get_room_temp()"""
    temp = pygw.get_room_temp()
    assert temp is None

    pygw._connected = True
    pygw._protocol = SimpleNamespace(status={v.THERMOSTAT: {v.DATA_ROOM_TEMP: 23.5}})

    temp = pygw.get_room_temp()
    assert temp == 23.5


def test_get_target_temp(pygw):
    """Test pyotgw.get_target_temp()"""
    assert pygw.get_target_temp() is None

    pygw._connected = True
    pygw._protocol = SimpleNamespace(
        status={v.THERMOSTAT: {v.DATA_ROOM_SETPOINT: 23.5}},
    )
    temp = pygw.get_target_temp()
    assert temp == 23.5

    pygw._protocol.status[v.THERMOSTAT][v.DATA_ROOM_SETPOINT_OVRD] = 20.5
    temp = pygw.get_target_temp()
    assert temp == 20.5


async def test_set_target_temp(pygw):
    """Test pyotgw.set_target_temp()"""
    with pytest.raises(TypeError):
        await pygw.set_target_temp(None)

    with patch.object(pygw, "_wait_for_cmd", return_value=None) as wait_for_cmd:
        assert await pygw.set_target_temp(12.3) is None

    wait_for_cmd.assert_called_once_with(
        v.OTGW_CMD_TARGET_TEMP, "12.3", v.OTGW_DEFAULT_TIMEOUT,
    )

    with patch.object(
        pygw, "_wait_for_cmd", return_value="0.00",
    ) as wait_for_cmd, patch.object(pygw, "_update_full_status") as update_full_status:
        temp = await pygw.set_target_temp(0, timeout=5)

    assert type(temp) == float
    assert temp == 0
    wait_for_cmd.assert_called_once_with(
        v.OTGW_CMD_TARGET_TEMP, "0.0", 5,
    )
    update_full_status.assert_called_once_with(
        {
            v.OTGW: {v.OTGW_SETP_OVRD_MODE: v.OTGW_SETP_OVRD_DISABLED},
            v.THERMOSTAT: {v.DATA_ROOM_SETPOINT_OVRD: None},
        }
    )

    with patch.object(
        pygw, "_wait_for_cmd", return_value="15.50",
    ) as wait_for_cmd, patch.object(pygw, "_update_full_status") as update_full_status:
        temp = await pygw.set_target_temp(15.5)

    assert temp == 15.5
    wait_for_cmd.assert_called_once_with(v.OTGW_CMD_TARGET_TEMP, "15.5", 3)
    update_full_status.assert_called_once_with(
        {
            v.OTGW: {v.OTGW_SETP_OVRD_MODE: v.OTGW_SETP_OVRD_TEMPORARY},
            v.THERMOSTAT: {v.DATA_ROOM_SETPOINT_OVRD: 15.5},
        }
    )

    with patch.object(
        pygw, "_wait_for_cmd", return_value="20.50",
    ) as wait_for_cmd, patch.object(pygw, "_update_full_status") as update_full_status:
        temp = await pygw.set_target_temp(20.5, temporary=False)

    assert temp == 20.5
    wait_for_cmd.assert_called_once_with(v.OTGW_CMD_TARGET_TEMP_CONST, "20.5", 3)
    update_full_status.assert_called_once_with(
        {
            v.OTGW: {v.OTGW_SETP_OVRD_MODE: v.OTGW_SETP_OVRD_PERMANENT},
            v.THERMOSTAT: {v.DATA_ROOM_SETPOINT_OVRD: 20.5},
        }
    )


def test_get_temp_sensor_function(pygw):
    """Test pyotgw.get_temp_sensor_function()"""
    assert pygw.get_temp_sensor_function() is None

    pygw._connected = True
    pygw._protocol = SimpleNamespace(status={v.OTGW: {v.OTGW_TEMP_SENSOR: "O"}})
    assert pygw.get_temp_sensor_function() == "O"


async def test_set_temp_sensor_function(pygw):
    """Test pyotgw.set_temp_sensor_function()"""
    assert await pygw.set_temp_sensor_function("P") is None

    with patch.object(pygw, "_wait_for_cmd", return_value=None) as wait_for_cmd:
        assert await pygw.set_temp_sensor_function("O") is None

    wait_for_cmd.assert_called_once_with(
        v.OTGW_CMD_TEMP_SENSOR, "O", v.OTGW_DEFAULT_TIMEOUT,
    )

    with patch.object(
        pygw, "_wait_for_cmd", return_value="R",
    ) as wait_for_cmd, patch.object(pygw, "_update_status") as update_status:
        assert await pygw.set_temp_sensor_function("R", timeout=5) == "R"

    wait_for_cmd.assert_called_once_with(v.OTGW_CMD_TEMP_SENSOR, "R", 5)
    update_status.assert_called_once_with(v.OTGW, {v.OTGW_TEMP_SENSOR: "R"})


def test_get_outside_temp(pygw):
    """Test pyotgw.get_outside_temp()"""
    assert pygw.get_outside_temp() is None

    pygw._connected = True
    pygw._protocol = SimpleNamespace(
        status={v.BOILER: {v.DATA_OUTSIDE_TEMP: -5.4}, v.THERMOSTAT: {}},
    )
    assert pygw.get_outside_temp() == -5.4

    pygw._protocol.status[v.THERMOSTAT][v.DATA_OUTSIDE_TEMP] = 15.5
    assert pygw.get_outside_temp() == 15.5


async def test_set_outside_temp(pygw):
    """Test pyotgw.set_outside_temp()"""
    assert await pygw.set_outside_temp(-40.1) is None

    with pytest.raises(TypeError):
        await pygw.set_outside_temp(None)

    with patch.object(pygw, "_wait_for_cmd", return_value=None) as wait_for_cmd:
        assert await pygw.set_outside_temp(0, timeout=5) is None

    wait_for_cmd.assert_called_once_with(v.OTGW_CMD_OUTSIDE_TEMP, "0.0", 5)

    with patch.object(
        pygw, "_wait_for_cmd", return_value="23.5",
    ) as wait_for_cmd, patch.object(pygw, "_update_status") as update_status:
        assert await pygw.set_outside_temp(23.5) == 23.5

    wait_for_cmd.assert_called_once_with(
        v.OTGW_CMD_OUTSIDE_TEMP, "23.5", v.OTGW_DEFAULT_TIMEOUT
    )
    update_status.assert_called_once_with(v.THERMOSTAT, {v.DATA_OUTSIDE_TEMP: 23.5})

    with patch.object(
        pygw, "_wait_for_cmd", return_value="-",
    ) as wait_for_cmd, patch.object(pygw, "_update_status") as update_status:
        assert await pygw.set_outside_temp(99) == "-"

    wait_for_cmd.assert_called_once_with(
        v.OTGW_CMD_OUTSIDE_TEMP, "99.0", v.OTGW_DEFAULT_TIMEOUT
    )
    update_status.assert_called_once_with(v.THERMOSTAT, {v.DATA_OUTSIDE_TEMP: 0.0})


async def test_set_clock(pygw):
    """Test pyotgw.set_clock()"""
    dt = datetime(year=2021, month=3, day=12, hour=12, minute=34)

    with patch.object(pygw, "_wait_for_cmd", return_value="12:34/5") as wait_for_cmd:
        assert await pygw.set_clock(dt) == "12:34/5"

    wait_for_cmd.assert_called_once_with(
        v.OTGW_CMD_SET_CLOCK, "12:34/5", v.OTGW_DEFAULT_TIMEOUT
    )

    with patch.object(pygw, "_wait_for_cmd", return_value="12:34/5") as wait_for_cmd:
        assert await pygw.set_clock(dt, timeout=5) == "12:34/5"

    wait_for_cmd.assert_called_once_with(v.OTGW_CMD_SET_CLOCK, "12:34/5", 5)


def test_get_hot_water_ovrd(pygw):
    """Test pyotgw.get_hot_water_ovrd()"""
    assert pygw.get_hot_water_ovrd() is None

    pygw._connected = True
    pygw._protocol = SimpleNamespace(status={v.OTGW: {v.OTGW_DHW_OVRD: 1}})
    assert pygw.get_hot_water_ovrd() == 1


async def test_get_reports(pygw):
    """Test pyotgw.get_reports()"""
    pygw._protocol = SimpleNamespace(
        status=copy.deepcopy(v.DEFAULT_STATUS), _updateq=asyncio.Queue(),
    )

    def get_response_42(cmd, val):
        """Get response from dict or raise ValueError"""
        try:
            return pygw_reports.report_responses_42[val]
        except KeyError:
            raise ValueError

    with patch.object(
        pygw,
        "_wait_for_cmd",
        side_effect=lambda _, v: pygw_reports.report_responses_51[v],
    ):
        assert await pygw.get_reports() == pygw_reports.expect_51

    pygw._protocol.status = copy.deepcopy(v.DEFAULT_STATUS)
    with patch.object(
        pygw, "_wait_for_cmd", side_effect=get_response_42,
    ):
        assert await pygw.get_reports() == pygw_reports.expect_42

    with patch.object(
        pygw, "_wait_for_cmd", side_effect=["OpenTherm Gateway 5.1", ValueError],
    ), pytest.raises(ValueError):
        await pygw.get_reports()


async def test_get_status(pygw):
    """Test pyotgw.get_status()"""
    pygw._protocol = SimpleNamespace(
        status=copy.deepcopy(v.DEFAULT_STATUS), _updateq=asyncio.Queue(),
    )
    pygw.loop = None
    with patch.object(
        pygw,
        "_wait_for_cmd",
        side_effect=[None, (None, pygw_status.status_5), (None, pygw_status.status_4)],
    ):
        assert await pygw.get_status() is None
        assert await pygw.get_status() == pygw_status.expect_5
        pygw._protocol.status = copy.deepcopy(v.DEFAULT_STATUS)
        assert await pygw.get_status() == pygw_status.expect_4


async def test_set_hot_water_ovrd(pygw):
    """Test pyotgw.set_hot_water_ovrd()"""
    pygw._protocol = SimpleNamespace(
        status=copy.deepcopy(v.DEFAULT_STATUS), _updateq=asyncio.Queue(),
    )
    with patch.object(
        pygw, "_wait_for_cmd", side_effect=[None, "A", "1"],
    ) as wait_for_cmd:
        assert await pygw.set_hot_water_ovrd(0) is None
        assert await pygw.set_hot_water_ovrd("A", 5) == "A"
        assert await pygw.set_hot_water_ovrd(1) == 1

    assert wait_for_cmd.call_count == 3
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_HOT_WATER, 0, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_HOT_WATER, "A", 5),
            call(v.OTGW_CMD_HOT_WATER, 1, v.OTGW_DEFAULT_TIMEOUT),
        ],
        any_order=False,
    )


def test_get_mode(pygw):
    """Test pyotgw.get_mode()"""
    assert pygw.get_mode() is None

    pygw._connected = True
    pygw._protocol = SimpleNamespace(status={v.OTGW: {v.OTGW_MODE: "M"}})

    assert pygw.get_mode() == "M"


async def test_set_mode(pygw):
    """Test pyotgw.set_mode()"""
    pygw._protocol = SimpleNamespace(
        status=copy.deepcopy(v.DEFAULT_STATUS), _updateq=asyncio.Queue(),
    )

    with patch.object(pygw, "_wait_for_cmd", side_effect=[None, v.OTGW_MODE_MONITOR]):
        assert await pygw.set_mode(v.OTGW_MODE_GATEWAY) is None
        assert await pygw.set_mode(v.OTGW_MODE_MONITOR) == v.OTGW_MODE_MONITOR

    with patch.object(
        pygw, "_wait_for_cmd", return_value=v.OTGW_MODE_RESET,
    ), patch.object(pygw, "get_reports") as get_reports, patch.object(
        pygw, "get_status",
    ) as get_status:
        assert await pygw.set_mode(v.OTGW_MODE_RESET) == v.DEFAULT_STATUS
        get_reports.assert_called_once()
        get_status.assert_called_once()


def test_get_led_mode(pygw):
    """Test pyotgw.get_led_mode()"""
    assert pygw.get_led_mode(None) is None

    pygw._connected = True
    pygw._protocol = SimpleNamespace(status={v.OTGW: {v.OTGW_LED_F: "C"}})

    assert pygw.get_led_mode("A") is None
    assert pygw.get_led_mode("F") == "C"


async def test_set_led_mode(pygw):
    """Test pyotgw.set_led_mode()"""
    assert await pygw.set_led_mode("G", "A") is None

    pygw._protocol = SimpleNamespace(status={v.OTGW: {}})
    with patch.object(
        pygw, "_wait_for_cmd", side_effect=[None, "X"],
    ) as wait_for_cmd, patch.object(pygw, "_update_status") as update_status:
        assert await pygw.set_led_mode("B", "H") is None
        assert await pygw.set_led_mode("A", "X", timeout=5) == "X"

    assert wait_for_cmd.call_count == 2
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_LED_B, "H", v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_LED_A, "X", 5),
        ],
        any_order=False,
    )

    update_status.assert_called_once_with(v.OTGW, {v.OTGW_LED_A: "X"})


def test_get_gpio_mode(pygw):
    """Test pyotgw.get_gpio_mode()"""
    assert pygw.get_gpio_mode(None) is None

    pygw._connected = True
    pygw._protocol = SimpleNamespace(status={v.OTGW: {v.OTGW_GPIO_A: 1}})

    assert pygw.get_gpio_mode("A") == 1
    assert pygw.get_gpio_mode("B") is None


async def test_set_gpio_mode(pygw):
    """Test pyotgw.set_gpio_mode()"""
    assert await pygw.set_gpio_mode("A", 9) is None

    pygw._protocol = SimpleNamespace(status={v.OTGW: {}})
    with patch.object(
        pygw, "_wait_for_cmd", side_effect=[None, 3],
    ) as wait_for_cmd, patch.object(pygw, "_update_status") as update_status:
        assert await pygw.set_gpio_mode("A", 7) is None
        assert await pygw.set_gpio_mode("A", 6) is None
        assert await pygw.set_gpio_mode("B", 3, timeout=5) == 3

    assert wait_for_cmd.call_count == 2
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_GPIO_A, 6, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_GPIO_B, 3, 5),
        ],
        any_order=False,
    )

    update_status.assert_called_once_with(v.OTGW, {v.OTGW_GPIO_B: 3})


def test_get_setback_temp(pygw):
    """Test pyotgw.get_gpio_mode()"""
    assert pygw.get_setback_temp() is None

    pygw._connected = True
    pygw._protocol = SimpleNamespace(status={v.OTGW: {}})

    assert pygw.get_setback_temp() is None
    pygw._protocol = SimpleNamespace(status={v.OTGW: {v.OTGW_SB_TEMP: 14.5}})
    assert pygw.get_setback_temp() == 14.5


async def test_set_setback_temp(pygw):
    """Test pyotgw.set_setback_temp()"""
    pygw._protocol = SimpleNamespace(status={v.OTGW: {}})
    with patch.object(
        pygw, "_wait_for_cmd", side_effect=[None, 16.5],
    ) as wait_for_cmd, patch.object(pygw, "_update_status") as update_status:
        assert await pygw.set_setback_temp(17.5) is None
        assert await pygw.set_setback_temp(16.5, 5) == 16.5

    assert wait_for_cmd.call_count == 2
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_SETBACK, 17.5, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_SETBACK, 16.5, 5),
        ],
        any_order=False,
    )

    update_status.assert_called_once_with(v.OTGW, {v.OTGW_SB_TEMP: 16.5})


async def test_add_alternative(pygw):
    """Test pyotgw.add_alternative()"""
    assert await pygw.add_alternative(0) is None

    with patch.object(pygw, "_wait_for_cmd", side_effect=[None, 23]) as wait_for_cmd:
        assert await pygw.add_alternative(20) is None
        assert await pygw.add_alternative(23, 5) == 23

    assert wait_for_cmd.call_count == 2
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_ADD_ALT, 20, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_ADD_ALT, 23, 5),
        ],
        any_order=False,
    )


async def test_del_alternative(pygw):
    """Test pyotgw.del_alternative()"""
    assert await pygw.del_alternative(0) is None

    with patch.object(pygw, "_wait_for_cmd", side_effect=[None, 23]) as wait_for_cmd:
        assert await pygw.del_alternative(20) is None
        assert await pygw.del_alternative(23, 5) == 23

    assert wait_for_cmd.call_count == 2
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_DEL_ALT, 20, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_DEL_ALT, 23, 5),
        ],
        any_order=False,
    )


async def test_add_unknown_id(pygw):
    """Test pyotgw.add_unknown_id()"""
    assert await pygw.add_unknown_id(0) is None

    with patch.object(pygw, "_wait_for_cmd", side_effect=[None, 23]) as wait_for_cmd:
        assert await pygw.add_unknown_id(20) is None
        assert await pygw.add_unknown_id(23, 5) == 23

    assert wait_for_cmd.call_count == 2
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_UNKNOWN_ID, 20, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_UNKNOWN_ID, 23, 5),
        ],
        any_order=False,
    )


async def test_del_unknown_id(pygw):
    """Test pyotgw.del_unknown_id()"""
    assert await pygw.del_unknown_id(0) is None

    with patch.object(pygw, "_wait_for_cmd", side_effect=[None, 23]) as wait_for_cmd:
        assert await pygw.del_unknown_id(20) is None
        assert await pygw.del_unknown_id(23, 5) == 23

    assert wait_for_cmd.call_count == 2
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_KNOWN_ID, 20, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_KNOWN_ID, 23, 5),
        ],
        any_order=False,
    )


async def test_prio_message(pygw):
    """TODO: Implement and test pyotgw.prio_message()"""
    assert await pygw.prio_message(None) is None


async def test_set_response(pygw):
    """TODO: Implement and test pyotgw.set_response()"""
    assert await pygw.set_response(None, None) is None


async def test_clear_response(pygw):
    """TODO: Implement and test pyotgw.clear_response()"""
    assert await pygw.clear_response(None) is None


async def test_set_max_ch_setpoint(pygw):
    """Test pyotgw.set_max_ch_setpoint()"""
    pygw._protocol = SimpleNamespace(status={v.OTGW: {}})
    with patch.object(
        pygw, "_wait_for_cmd", side_effect=[None, 74.5],
    ) as wait_for_cmd, patch.object(pygw, "_update_status") as update_status:
        assert await pygw.set_max_ch_setpoint(75.5) is None
        assert await pygw.set_max_ch_setpoint(74.5, 5) == 74.5

    assert wait_for_cmd.call_count == 2
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_SET_MAX, 75.5, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_SET_MAX, 74.5, 5),
        ],
        any_order=False,
    )

    update_status.assert_called_once_with(v.BOILER, {v.DATA_MAX_CH_SETPOINT: 74.5})


async def test_set_dhw_setpoint(pygw):
    """Test pyotgw.set_dhw_setpoint()"""
    pygw._protocol = SimpleNamespace(status={v.OTGW: {}})
    with patch.object(
        pygw, "_wait_for_cmd", side_effect=[None, 54.5],
    ) as wait_for_cmd, patch.object(pygw, "_update_status") as update_status:
        assert await pygw.set_dhw_setpoint(55.5) is None
        assert await pygw.set_dhw_setpoint(54.5, 5) == 54.5

    assert wait_for_cmd.call_count == 2
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_SET_WATER, 55.5, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_SET_WATER, 54.5, 5),
        ],
        any_order=False,
    )

    update_status.assert_called_once_with(v.BOILER, {v.DATA_DHW_SETPOINT: 54.5})


async def test_set_max_relative_mod(pygw):
    """Test pyotgw.set_max_relative_mod()"""
    assert await pygw.set_max_relative_mod(-1) is None

    pygw._protocol = SimpleNamespace(status={v.BOILER: {}})
    with patch.object(
        pygw, "_wait_for_cmd", side_effect=[None, "-", 55],
    ) as wait_for_cmd, patch.object(pygw, "_update_status") as update_status:
        assert await pygw.set_max_relative_mod(56) is None
        assert await pygw.set_max_relative_mod(54, 5) == "-"
        assert await pygw.set_max_relative_mod(55) == 55

    assert wait_for_cmd.call_count == 3
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_MAX_MOD, 56, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_MAX_MOD, 54, 5),
            call(v.OTGW_CMD_MAX_MOD, 55, v.OTGW_DEFAULT_TIMEOUT),
        ],
        any_order=False,
    )

    assert update_status.call_count == 2
    update_status.assert_has_calls(
        [
            call(v.BOILER, {v.DATA_SLAVE_MAX_RELATIVE_MOD: None}),
            call(v.BOILER, {v.DATA_SLAVE_MAX_RELATIVE_MOD: 55}),
        ],
        any_order=False,
    )


async def test_set_control_setpoint(pygw):
    """Test pyotgw.set_control_setpoint()"""
    pygw._protocol = SimpleNamespace(status={v.BOILER: {}})
    with patch.object(
        pygw, "_wait_for_cmd", side_effect=[None, 19.5],
    ) as wait_for_cmd, patch.object(pygw, "_update_status") as update_status:
        assert await pygw.set_control_setpoint(21.5) is None
        assert await pygw.set_control_setpoint(19.5, 5) == 19.5

    assert wait_for_cmd.call_count == 2
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_CONTROL_SETPOINT, 21.5, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_CONTROL_SETPOINT, 19.5, 5),
        ],
        any_order=False,
    )

    update_status.assert_called_once_with(v.BOILER, {v.DATA_CONTROL_SETPOINT: 19.5})


async def test_set_control_setpoint_2(pygw):
    """Test pyotgw.set_control_setpoint_2()"""
    pygw._protocol = SimpleNamespace(status={v.BOILER: {}})
    with patch.object(
        pygw, "_wait_for_cmd", side_effect=[None, 19.5],
    ) as wait_for_cmd, patch.object(pygw, "_update_status") as update_status:
        assert await pygw.set_control_setpoint_2(21.5) is None
        assert await pygw.set_control_setpoint_2(19.5, 5) == 19.5

    assert wait_for_cmd.call_count == 2
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_CONTROL_SETPOINT_2, 21.5, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_CONTROL_SETPOINT_2, 19.5, 5),
        ],
        any_order=False,
    )

    update_status.assert_called_once_with(v.BOILER, {v.DATA_CONTROL_SETPOINT_2: 19.5})


async def test_set_ch_enable_bit(pygw):
    """Test pyotgw.set_ch_enable_bit()"""
    assert await pygw.set_ch_enable_bit(None) is None

    pygw._protocol = SimpleNamespace(status={v.BOILER: {}})
    with patch.object(
        pygw, "_wait_for_cmd", side_effect=[None, 1],
    ) as wait_for_cmd, patch.object(pygw, "_update_status") as update_status:
        assert await pygw.set_ch_enable_bit(0) is None
        assert await pygw.set_ch_enable_bit(1, 5) == 1

    assert wait_for_cmd.call_count == 2
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_CONTROL_HEATING, 0, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_CONTROL_HEATING, 1, 5),
        ],
        any_order=False,
    )

    update_status.assert_called_once_with(v.BOILER, {v.DATA_MASTER_CH_ENABLED: 1})


async def test_set_ch2_enable_bit(pygw):
    """Test pyotgw.set_ch2_enable_bit()"""
    assert await pygw.set_ch2_enable_bit(None) is None

    pygw._protocol = SimpleNamespace(status={v.BOILER: {}})
    with patch.object(
        pygw, "_wait_for_cmd", side_effect=[None, 1],
    ) as wait_for_cmd, patch.object(pygw, "_update_status") as update_status:
        assert await pygw.set_ch2_enable_bit(0) is None
        assert await pygw.set_ch2_enable_bit(1, 5) == 1

    assert wait_for_cmd.call_count == 2
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_CONTROL_HEATING_2, 0, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_CONTROL_HEATING_2, 1, 5),
        ],
        any_order=False,
    )

    update_status.assert_called_once_with(v.BOILER, {v.DATA_MASTER_CH2_ENABLED: 1})


async def test_set_ventilation(pygw):
    """Test pyotgw.set_ventilation()"""
    assert await pygw.set_ventilation(-1) is None

    pygw._protocol = SimpleNamespace(status={v.BOILER: {}})
    with patch.object(
        pygw, "_wait_for_cmd", side_effect=[None, 75],
    ) as wait_for_cmd, patch.object(pygw, "_update_status") as update_status:
        assert await pygw.set_ventilation(25) is None
        assert await pygw.set_ventilation(75, 5) == 75

    assert wait_for_cmd.call_count == 2
    wait_for_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_VENT, 25, v.OTGW_DEFAULT_TIMEOUT),
            call(v.OTGW_CMD_VENT, 75, 5),
        ],
        any_order=False,
    )

    update_status.assert_called_once_with(v.BOILER, {v.DATA_COOLING_CONTROL: 75})


def test_subscribe_and_unsubscribe(pygw):
    """Test pyotgw.subscribe() and pyotgw.unsubscribe()"""

    async def empty_callback(status):
        return

    async def empty_callback_2(status):
        return

    assert pygw.subscribe(empty_callback)
    assert pygw.subscribe(empty_callback_2)
    assert not pygw.subscribe(empty_callback_2)

    assert pygw._notify == [empty_callback, empty_callback_2]

    assert pygw.unsubscribe(empty_callback)
    assert not pygw.unsubscribe(empty_callback)

    assert pygw._notify == [empty_callback_2]


async def test_send_report(pygw):
    """Test pyotgw._send_report()"""
    mock_coro = MagicMock(return_value=asyncio.Future())
    mock_coro2 = MagicMock(return_value=asyncio.Future())

    pygw._notify = [mock_coro, mock_coro2]
    await pygw._send_report(v.DEFAULT_STATUS)

    for coro in (mock_coro, mock_coro2):
        coro.assert_called_once_with(v.DEFAULT_STATUS)


async def test_wait_for_cmd(caplog, pygw, pygw_proto):
    """Test pyotgw.wait_for_cmd()"""
    assert await pygw._wait_for_cmd(None, None) is None

    pygw._connected = True
    with patch.object(
        pygw_proto,
        "issue_cmd",
        side_effect=[None, "0", asyncio.TimeoutError, ValueError],
    ) as issue_cmd, caplog.at_level(logging.ERROR):
        assert await pygw._wait_for_cmd(v.OTGW_CMD_MODE, "G") is None
        assert await pygw._wait_for_cmd(v.OTGW_CMD_SUMMARY, 0) == "0"
        assert await pygw._wait_for_cmd(v.OTGW_CMD_REPORT, "I", 1) is None
        assert await pygw._wait_for_cmd(v.OTGW_CMD_MAX_MOD, -1) is None

    assert issue_cmd.await_count == 4
    issue_cmd.assert_has_awaits(
        [
            call(v.OTGW_CMD_MODE, "G"),
            call(v.OTGW_CMD_SUMMARY, 0),
            call(v.OTGW_CMD_REPORT, "I"),
            call(v.OTGW_CMD_MAX_MOD, -1),
        ],
        any_order=False,
    )

    assert caplog.record_tuples == [
        (
            "pyotgw.pyotgw",
            logging.ERROR,
            f"Timed out waiting for command: {v.OTGW_CMD_REPORT}, value: I.",
        ),
        (
            "pyotgw.pyotgw",
            logging.ERROR,
            f"Command {v.OTGW_CMD_MAX_MOD} with value -1 raised exception: ",
        ),
    ]


async def test_poll_gpio(caplog, pygw):
    """Test pyotgw._poll_gpio()"""
    pygw._gpio_task = None
    pygw.loop = asyncio.get_running_loop()
    pygw._protocol = SimpleNamespace(
        status={v.OTGW: {v.OTGW_GPIO_A: 4, v.OTGW_GPIO_B: 1}},
    )

    await pygw._poll_gpio()
    assert len(caplog.records) == 0

    pygw._protocol.status[v.OTGW][v.OTGW_GPIO_B] = 0
    with patch.object(
        pygw, "_wait_for_cmd", return_value="I=10",
    ) as wait_for_cmd, patch.object(
        pygw, "_update_status",
    ) as update_status, caplog.at_level(
        logging.DEBUG
    ):
        await pygw._poll_gpio()
        await asyncio.sleep(0)

    assert type(pygw._gpio_task) == asyncio.Task
    wait_for_cmd.assert_awaited_once_with(v.OTGW_CMD_REPORT, v.OTGW_REPORT_GPIO_STATES)
    update_status.assert_called_once_with(
        v.OTGW, {v.OTGW_GPIO_A_STATE: 1, v.OTGW_GPIO_B_STATE: 0},
    )
    assert caplog.record_tuples == [
        ("pyotgw.pyotgw", logging.DEBUG, "Starting GPIO polling routine"),
    ]

    caplog.clear()
    pygw._protocol.status[v.OTGW][v.OTGW_GPIO_B] = 1
    with patch.object(pygw, "_update_status") as update_status, caplog.at_level(
        logging.DEBUG
    ):
        await pygw._poll_gpio()
        await asyncio.sleep(0)

    assert pygw._gpio_task is None
    update_status.assert_called_once_with(
        v.OTGW, {v.OTGW_GPIO_A_STATE: 0, v.OTGW_GPIO_B_STATE: 0},
    )
    assert caplog.record_tuples == [
        ("pyotgw.pyotgw", logging.DEBUG, "Stopping GPIO polling routine"),
        ("pyotgw.pyotgw", logging.DEBUG, "GPIO polling routine stopped"),
    ]


def test_update_status(caplog, pygw):
    """Test pyotgw._update_status()"""
    pygw._protocol = SimpleNamespace(status=copy.deepcopy(v.DEFAULT_STATUS),)
    with caplog.at_level(logging.WARNING):
        pygw._update_status(v.BOILER, {})

    assert caplog.record_tuples == [
        (
            "pyotgw.pyotgw",
            logging.WARNING,
            "Error sending status update. Are we connected to the gateway?",
        ),
    ]
    caplog.clear()

    pygw._protocol = SimpleNamespace(
        status=copy.deepcopy(v.DEFAULT_STATUS), _updateq=asyncio.Queue(),
    )

    with caplog.at_level(logging.ERROR):
        pygw._update_status("test", {})

    assert caplog.record_tuples == [
        ("pyotgw.pyotgw", logging.ERROR, "Invalid status part for update: test"),
    ]
    caplog.clear()

    pygw._update_status(v.BOILER, {v.DATA_CONTROL_SETPOINT: 1.5})
    pygw._update_status(v.OTGW, {v.OTGW_ABOUT: "test value"})
    pygw._update_status(v.THERMOSTAT, {v.DATA_ROOM_SETPOINT: 20})

    assert pygw._protocol.status == {
        v.BOILER: {v.DATA_CONTROL_SETPOINT: 1.5},
        v.OTGW: {v.OTGW_ABOUT: "test value"},
        v.THERMOSTAT: {v.DATA_ROOM_SETPOINT: 20},
    }
    assert pygw._protocol._updateq.qsize() == 3
    assert pygw._protocol._updateq.get_nowait() == {
        v.BOILER: {v.DATA_CONTROL_SETPOINT: 1.5},
        v.OTGW: {},
        v.THERMOSTAT: {},
    }
    assert pygw._protocol._updateq.get_nowait() == {
        v.BOILER: {v.DATA_CONTROL_SETPOINT: 1.5},
        v.OTGW: {v.OTGW_ABOUT: "test value"},
        v.THERMOSTAT: {},
    }
    assert pygw._protocol._updateq.get_nowait() == {
        v.BOILER: {v.DATA_CONTROL_SETPOINT: 1.5},
        v.OTGW: {v.OTGW_ABOUT: "test value"},
        v.THERMOSTAT: {v.DATA_ROOM_SETPOINT: 20},
    }


def test_update_full_status(caplog, pygw):
    """Test pyotgw._update_full_status()"""
    pygw._protocol = SimpleNamespace(status=copy.deepcopy(v.DEFAULT_STATUS),)
    with caplog.at_level(logging.WARNING):
        pygw._update_full_status({})

    assert caplog.record_tuples == [
        (
            "pyotgw.pyotgw",
            logging.WARNING,
            "Error sending status update. Are we connected to the gateway?",
        ),
    ]
    caplog.clear()

    pygw._protocol = SimpleNamespace(
        status=copy.deepcopy(v.DEFAULT_STATUS), _updateq=asyncio.Queue(),
    )

    with caplog.at_level(logging.ERROR):
        pygw._update_full_status({"test": {}})

    assert caplog.record_tuples == [
        ("pyotgw.pyotgw", logging.ERROR, "Invalid status part for update: test"),
    ]
    caplog.clear()

    pygw._update_full_status(
        {
            v.BOILER: {v.DATA_CONTROL_SETPOINT: 1.5},
            v.OTGW: {v.OTGW_ABOUT: "test value"},
            v.THERMOSTAT: {v.DATA_ROOM_SETPOINT: 20},
        }
    )

    assert pygw._protocol.status == {
        v.BOILER: {v.DATA_CONTROL_SETPOINT: 1.5},
        v.OTGW: {v.OTGW_ABOUT: "test value"},
        v.THERMOSTAT: {v.DATA_ROOM_SETPOINT: 20},
    }
    assert pygw._protocol._updateq.qsize() == 1
    assert pygw._protocol._updateq.get_nowait() == {
        v.BOILER: {v.DATA_CONTROL_SETPOINT: 1.5},
        v.OTGW: {v.OTGW_ABOUT: "test value"},
        v.THERMOSTAT: {v.DATA_ROOM_SETPOINT: 20},
    }


def test_get_retry_timeout(pygw):
    """Test pyotgw._get_retry_timeout()"""
    from pyotgw.pyotgw import MAX_RETRY_TIMEOUT

    pygw._retry_timeout = MAX_RETRY_TIMEOUT / 2
    assert pygw._get_retry_timeout() == MAX_RETRY_TIMEOUT / 2
    assert pygw._get_retry_timeout() == (MAX_RETRY_TIMEOUT / 2) * 1.5
    assert pygw._get_retry_timeout() == MAX_RETRY_TIMEOUT
